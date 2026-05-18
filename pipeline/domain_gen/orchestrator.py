"""Pipeline orchestrator — Prompt 1 decomposition + subdomain iteration."""

from __future__ import annotations

import json
import logging
import re

import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .agent import SPARKY_BASE, SPARKY_MODEL, run_term_emission
from .models import DomainDecomposition, Term, terms_to_upload_json
from .prompts import PROMPT_1_SYSTEM, format_prompt_1_user

logger = logging.getLogger(__name__)


def _call_text(messages: list[dict], base_url: str, model: str) -> str:
    """Make a non-streaming text-only request and return the content.

    Args:
        messages: Chat messages list.
        base_url: Qwen API base URL.
        model: Model identifier.

    Returns:
        Content string from the model response.
    """
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 8192,
        "temperature": 0.3,
        "stream": False,
        "skip_rag": True,
        # Suppress extended thinking for Qwen3 on vLLM — Prompt 1 needs plain JSON,
        # not a reasoning chain that buries the answer in a fenced block.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    resp = requests.post(
        f"{base_url}/chat/completions",
        json=payload,
        timeout=(30, 300),
        verify=False,
    )
    resp.raise_for_status()
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = (msg.get("content") or "").strip()
    if not content:
        # Thinking models sometimes emit the answer inside the reasoning field
        content = (msg.get("reasoning") or "").strip()
        if content:
            logger.info("Prompt 1: content field empty, falling back to reasoning field")
    logger.info(f"Prompt 1 raw response ({len(content)} chars): {content[:300]!r}")
    return content


def decompose_domain(
    topic: str,
    hints: str = "",
    base_url: str = SPARKY_BASE,
    model: str = SPARKY_MODEL,
) -> DomainDecomposition:
    """Call Prompt 1 and parse the subdomain decomposition.

    Args:
        topic: Domain topic string.
        hints: Optional user focus hints.
        base_url: Qwen API base URL.
        model: Model identifier.

    Returns:
        Parsed DomainDecomposition.

    Raises:
        json.JSONDecodeError: If the model response is not valid JSON.
        ValueError: If the response does not match the expected schema.
    """
    messages = [
        {"role": "system", "content": PROMPT_1_SYSTEM},
        {"role": "user", "content": format_prompt_1_user(topic, hints)},
    ]
    raw = _call_text(messages, base_url, model)

    # Extract the last fenced JSON block — the model may produce a template
    # placeholder block early in its reasoning before writing the real answer.
    # Searching last-to-first finds the final, real JSON output.
    json_block: str | None = None
    for m in reversed(list(re.finditer(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", raw))):
        candidate = m.group(1).strip()
        if candidate.startswith("{"):
            json_block = candidate
            break

    # Fallback: find the last standalone { } block that parses cleanly
    if json_block is None:
        end_idx = len(raw) - 1
        while end_idx >= 0:
            end_idx = raw.rfind("}", 0, end_idx + 1)
            if end_idx == -1:
                break
            depth = 0
            for i in range(end_idx, -1, -1):
                if raw[i] == "}":
                    depth += 1
                elif raw[i] == "{":
                    depth -= 1
                    if depth == 0:
                        json_block = raw[i : end_idx + 1]
                        break
            if json_block:
                break

    if not json_block:
        logger.error(f"No JSON object found in response:\n{raw}")
        raise json.JSONDecodeError("No JSON object found", raw, 0)

    try:
        data = json.loads(json_block)
    except json.JSONDecodeError:
        logger.error(f"JSON parse failed. Extracted block:\n{json_block}")
        raise
    return DomainDecomposition(**data)


def run_pipeline(
    topic: str,
    hints: str = "",
    total_terms: int = 50,
    base_url: str = SPARKY_BASE,
    model: str = SPARKY_MODEL,
) -> tuple[DomainDecomposition, dict]:
    """Run the full two-prompt domain generation pipeline.

    Calls Prompt 1 once to decompose the domain, then calls Prompt 2 once
    per subdomain, distributing total_terms evenly across subdomains.

    Args:
        topic: Domain topic to generate.
        hints: Optional focus hints passed to Prompt 1.
        total_terms: Total target term count across all subdomains.
        base_url: Qwen API base URL.
        model: Model identifier.

    Returns:
        Tuple of (DomainDecomposition, upload_json_dict).
    """
    logger.info(f"Decomposing domain: {topic!r}")
    decomposition = decompose_domain(topic, hints, base_url, model)
    n = len(decomposition.subdomains)
    logger.info(f"Subdomains ({n}): {[s.name for s in decomposition.subdomains]}")

    target_per = max(1, total_terms // n)
    subdomain_terms: dict[str, list[Term]] = {}

    for i, subdomain in enumerate(decomposition.subdomains, 1):
        logger.info(f"[{i}/{n}] {subdomain.name!r} — target {target_per} terms")
        terms = run_term_emission(
            domain_name=topic,
            subdomain=subdomain,
            target_count=target_per,
            base_url=base_url,
            model=model,
        )
        subdomain_terms[subdomain.name] = terms
        logger.info(f"  collected {len(terms)} terms")

    total = sum(len(t) for t in subdomain_terms.values())
    logger.info(f"Pipeline complete: {total} terms across {n} subdomains")

    return decomposition, terms_to_upload_json(decomposition, subdomain_terms)
