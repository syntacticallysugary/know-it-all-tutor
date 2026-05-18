"""Prompt 2 agent loop — tool-calling term emission for one subdomain."""

from __future__ import annotations

import json
import logging
import time

import urllib3
import requests

from .models import Subdomain, Term
from .prompts import PROMPT_2_SYSTEM, format_prompt_2_user
from .tools import TOOL_DEFINITIONS, scrape_page, search_web

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

SPARKY_BASE = "https://192.168.1.105/lite/v1"
SPARKY_MODEL = "thinker1"


def _stream_call(messages: list[dict], base_url: str, model: str) -> dict:
    """Make a streaming tool-calling request to Sparky.

    Returns:
        Dict with finish_reason and message keys.
    """
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOL_DEFINITIONS,
        "tool_choice": "auto",
        "max_tokens": 8192,
        "temperature": 0.3,
        "stream": True,
        "skip_rag": True,
        "chat_template_kwargs": {"enable_thinking": True},
    }

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls_acc: dict[int, dict] = {}
    finish_reason: str | None = None

    with requests.post(
        f"{base_url}/chat/completions",
        json=payload,
        stream=True,
        timeout=(30, None),
        verify=False,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw or not raw.startswith(b"data: "):
                continue
            data = raw[6:]
            if data == b"[DONE]":
                break
            chunk = json.loads(data)
            if "error" in chunk:
                raise RuntimeError(f"LLM error response: {chunk['error']}")
            if not chunk.get("choices"):
                continue
            choice = chunk["choices"][0]
            finish_reason = choice.get("finish_reason") or finish_reason
            delta = choice.get("delta", {})

            if delta.get("content"):
                content_parts.append(delta["content"])
            if delta.get("reasoning"):
                reasoning_parts.append(delta["reasoning"])

            for tc in delta.get("tool_calls") or []:
                i = tc["index"]
                if i not in tool_calls_acc:
                    tool_calls_acc[i] = {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                if tc.get("id"):
                    tool_calls_acc[i]["id"] = tc["id"]
                fn = tc.get("function", {})
                if fn.get("name"):
                    tool_calls_acc[i]["function"]["name"] += fn["name"]
                if fn.get("arguments"):
                    tool_calls_acc[i]["function"]["arguments"] += fn["arguments"]

    return {
        "finish_reason": finish_reason,
        "message": {
            "role": "assistant",
            "content": "".join(content_parts) or None,
            "reasoning": "".join(reasoning_parts) or None,
            "tool_calls": list(tool_calls_acc.values()),
        },
    }


def _dispatch(name: str, args: dict, emitted: list[Term], target: int) -> str:
    """Execute one tool call and return the result string.

    Args:
        name: Tool name.
        args: Parsed tool arguments.
        emitted: Running list of emitted terms — mutated in place by emit_term.
        target: Target term count, included in emit_term feedback.

    Returns:
        Result string to pass back to the model.
    """
    if name == "search_web":
        results = search_web(args.get("query", ""))
        return json.dumps(results, indent=2)

    if name == "scrape_page":
        return scrape_page(args.get("url", ""))

    if name == "emit_term":
        try:
            term = Term(**{k: v for k, v in args.items() if k in Term.model_fields})
            emitted.append(term)
            logger.info(f"  → emitted [{len(emitted)}/{target}]: {term.term!r}")
            return f"Recorded '{term.term}'. Total emitted: {len(emitted)}/{target}."
        except Exception as exc:
            return f"emit_term validation error: {exc}"

    return f"Unknown tool: {name}"


def run_term_emission(
    domain_name: str,
    subdomain: Subdomain,
    target_count: int,
    base_url: str = SPARKY_BASE,
    model: str = SPARKY_MODEL,
    max_turns: int = 25,
) -> list[Term]:
    """Run the Prompt 2 agent loop for one subdomain.

    Args:
        domain_name: Parent domain name passed to the user prompt.
        subdomain: Subdomain to research.
        target_count: Number of terms to emit before stopping.
        base_url: Qwen API base URL.
        model: Model identifier.
        max_turns: Hard cap on agent loop iterations.

    Returns:
        List of emitted Terms.
    """
    emitted: list[Term] = []
    messages: list[dict] = [
        {"role": "system", "content": PROMPT_2_SYSTEM},
        {"role": "user", "content": format_prompt_2_user(domain_name, subdomain, target_count)},
    ]

    for turn in range(max_turns):
        if len(emitted) >= target_count:
            logger.info(f"  Target {target_count} reached after {turn} turns.")
            break

        result = None
        for attempt in range(3):
            try:
                result = _stream_call(messages, base_url, model)
                break
            except Exception as exc:
                if attempt < 2:
                    wait = 30 * (attempt + 1)
                    logger.warning(f"  LLM call failed (attempt {attempt + 1}/3): {exc}. Retrying in {wait}s.")
                    time.sleep(wait)
                else:
                    logger.warning(f"  LLM call failed at turn {turn + 1} after 3 attempts: {exc}. Stopping with {len(emitted)} terms.")
        if result is None:
            break
        msg = result["message"]

        # Strip malformed tool calls before storing in history. The server rejects
        # requests if the history contains tool calls with unparseable arguments,
        # empty ids, or missing names. Also drop the non-standard reasoning field.
        valid_tool_calls = []
        for tc in msg.get("tool_calls") or []:
            if not (tc.get("id") and tc["function"].get("name")):
                continue
            try:
                json.loads(tc["function"].get("arguments") or "{}")
                valid_tool_calls.append(tc)
            except json.JSONDecodeError:
                logger.warning(f"  dropping tool call with unparseable arguments: {tc['function']['name']!r}")
        msg = {
            "role": "assistant",
            "content": msg.get("content"),
            "tool_calls": valid_tool_calls,
        }
        messages.append(msg)

        # Sliding window: keep system + user + last 8 messages of history.
        # Each turn adds 1 assistant + 1-4 tool result messages; 8 slots ≈ 2-3 turns.
        # Prevents context from growing large enough to OOM vLLM.
        if len(messages) > 10:
            messages = messages[:2] + messages[-8:]

        tool_calls = valid_tool_calls
        finish = result.get("finish_reason", "stop")

        if not tool_calls:
            logger.info(
                f"  Agent stopped (finish={finish}, turn={turn + 1}, emitted={len(emitted)})"
            )
            break

        tool_results: list[dict] = []
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}
                logger.warning(f"  turn {turn + 1}: malformed arguments for {name!r}")

            logger.debug(f"  turn {turn + 1}: {name}({list(args.keys())})")
            output = _dispatch(name, args, emitted, target_count)
            # Cap tool result size to prevent context window overflow
            if len(output) > 2000:
                output = output[:2000] + "\n[truncated]"
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": output,
            })
        messages.extend(tool_results)

    return emitted
