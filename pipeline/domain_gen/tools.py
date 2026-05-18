"""Web search and scraping tools + OpenAI-compatible tool definitions.

search_web and scrape_page delegate to the ske-search MCP server
(http://localhost:8890/mcp) via its HTTP transport. The server aggregates
multiple search engines and is the preferred search mechanism per project
policy. Both functions raise RuntimeError if the server is unreachable so
the caller gets a clear signal rather than a silent fallback.
"""

from __future__ import annotations

import json
import logging

import requests

logger = logging.getLogger(__name__)

_SKE_URL = "http://localhost:8890/mcp"
_SKE_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
_REQ_ID = 0
_SKE_SESSION_ID: str | None = None


def _ske_initialize() -> None:
    """Perform the MCP initialize handshake and store the session ID.

    The Streamable HTTP transport requires an initialize call before tools/call.
    The server returns a Mcp-Session-Id header that must accompany all subsequent
    requests in this session.
    """
    global _SKE_SESSION_ID, _REQ_ID
    _REQ_ID += 1
    payload = {
        "jsonrpc": "2.0",
        "id": str(_REQ_ID),
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "domain-gen-worker", "version": "1.0.0"},
        },
    }
    try:
        resp = requests.post(_SKE_URL, json=payload, headers=_SKE_HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"ske-search init failed: {exc}") from exc

    session_id = resp.headers.get("Mcp-Session-Id")
    if not session_id:
        # Some implementations return the session ID in the body
        try:
            body = resp.json()
            session_id = body.get("result", {}).get("sessionId")
        except Exception:
            pass

    _SKE_SESSION_ID = session_id
    logger.info(f"ske-search session initialized (id={session_id!r})")


def _ske_call(tool_name: str, arguments: dict) -> str:
    """Call a ske-search MCP tool via its HTTP transport.

    Args:
        tool_name: MCP tool name (web_search or scrape_page).
        arguments: Tool arguments dict.

    Returns:
        Text content from the MCP response.

    Raises:
        RuntimeError: If the ske-search server is unreachable or returns an error.
    """
    global _REQ_ID, _SKE_SESSION_ID
    if _SKE_SESSION_ID is None:
        _ske_initialize()

    _REQ_ID += 1
    headers = dict(_SKE_HEADERS)
    if _SKE_SESSION_ID:
        headers["Mcp-Session-Id"] = _SKE_SESSION_ID

    payload = {
        "jsonrpc": "2.0",
        "id": str(_REQ_ID),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    try:
        resp = requests.post(_SKE_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"ske-search server unreachable at {_SKE_URL}: {exc}") from exc

    # Handle SSE response (text/event-stream) or plain JSON
    content_type = resp.headers.get("Content-Type", "")
    if "text/event-stream" in content_type:
        text = _parse_sse(resp.text)
    else:
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"ske-search error: {data['error']}")
        text = _extract_text(data.get("result", {}))

    return text


def _parse_sse(body: str) -> str:
    """Extract the result text from an SSE response body."""
    for line in body.splitlines():
        if line.startswith("data:"):
            raw = line[5:].strip()
            if raw and raw != "[DONE]":
                try:
                    data = json.loads(raw)
                    return _extract_text(data.get("result", data))
                except json.JSONDecodeError:
                    continue
    return body


def _extract_text(result: dict) -> str:
    """Pull the text value out of an MCP tool result."""
    content = result.get("content", [])
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
    return str(result)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via ske-search and return URLs, titles, and snippets.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with url, title, snippet keys, or a single error dict.
    """
    try:
        raw = _ske_call("web_search", {"query": query, "max_results": max_results})
        # Try a JSON array first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed[:max_results]
        except json.JSONDecodeError:
            pass
        # ske-search returns concatenated pretty-printed JSON objects
        # Use raw_decode to consume one object at a time
        results = []
        decoder = json.JSONDecoder()
        pos = 0
        raw_stripped = raw.strip()
        while pos < len(raw_stripped) and len(results) < max_results:
            while pos < len(raw_stripped) and raw_stripped[pos] in " \t\n\r":
                pos += 1
            if pos >= len(raw_stripped):
                break
            try:
                obj, pos = decoder.raw_decode(raw_stripped, pos)
                if isinstance(obj, dict):
                    results.append(obj)
            except json.JSONDecodeError:
                break
        if results:
            return results
        return [{"snippet": raw}]
    except Exception as exc:
        logger.warning(f"search_web failed for {query!r}: {exc}")
        return [{"error": str(exc)}]


def scrape_page(url: str, max_chars: int = 3000) -> str:
    """Fetch a web page via ske-search and return cleaned plain text.

    Args:
        url: URL to fetch.
        max_chars: Maximum characters to return.

    Returns:
        Cleaned text content, truncated to max_chars.
    """
    try:
        text = _ske_call("scrape_page", {"url": url})
        return text[:max_chars]
    except Exception as exc:
        logger.warning(f"scrape_page failed for {url!r}: {exc}")
        return f"Error fetching {url}: {exc}"


TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web and return URLs, titles, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_page",
            "description": "Fetch and return cleaned plain text from a web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_term",
            "description": "Record one completed term. Call once per term — do not batch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"},
                    "short_reference": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced", "unverified"],
                    },
                    "category": {"type": "string"},
                    "example": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["term", "definition", "short_reference", "difficulty", "category"],
            },
        },
    },
]
