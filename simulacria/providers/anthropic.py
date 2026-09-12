"""Anthropic Messages API. The verified path: every model marked verified uses it.

`max_retries=0` on the client is deliberate. The SDK would otherwise retry a 429
out of sight, and a paid attempt without its own receipt is exactly what the
manifest exists to rule out.
"""

from __future__ import annotations

import json

import anthropic

from simulacria.providers.base import RecordedAPIError, UnusableResponse  # noqa: F401

KEY_VARIABLE = "LLM_API_KEY"
KEY_PREFIX = "sk-ant-"


def accepts_key(key: str) -> bool:
    return key.startswith(KEY_PREFIX)


def build_payload(spec, instructions: str, text: str, max_tokens: int) -> dict:
    # No refusal fallbacks, deliberately: a fallback re-runs a refused request on
    # a different model in silence. A refusal is data, and the model stays pinned.
    payload = {
        "model": spec.model,
        "max_tokens": max_tokens,
        "system": instructions,
        "messages": [{"role": "user", "content": text}],
    }
    # Only models that accept the parameter get it: Haiku 4.5 answers `effort`
    # with HTTP 400, so the registry leaves its params empty.
    if spec.params:
        payload["output_config"] = dict(spec.params)
    return payload


def with_schema(payload: dict, schema: dict) -> dict:
    """Constrain the reply to a JSON schema. Syntax only -- not semantic correctness."""
    payload["output_config"] = {**payload.get("output_config", {}), "format": schema}
    return payload


def request_input(payload: dict) -> str:
    return payload["messages"][0]["content"]


def request_instructions(payload: dict) -> str:
    return payload["system"]


def _client(key: str, timeout: int) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=key, max_retries=0, timeout=timeout)


def post(payload: dict, key: str, timeout: int = 300) -> tuple[int, bytes]:
    """One attempt, returning the status and the exact response bytes."""
    try:
        raw = _client(key, timeout).messages.with_raw_response.create(**payload)
        return raw.status_code, raw.content
    except anthropic.APIStatusError as error:
        return error.status_code, error.response.content
    except anthropic.APIConnectionError:
        # An OSError, so callers keep the worst-case budget hold: with no response
        # there is no proof the request was not processed and billed. No message
        # text is carried -- transport errors can echo request details.
        raise ConnectionError("Anthropic API unreachable") from None


def decode(raw: bytes, spec) -> tuple[str, dict]:
    response = json.loads(raw)
    stop = response.get("stop_reason")
    if stop == "refusal":
        details = response.get("stop_details") or {}
        category = details.get("category") if isinstance(details, dict) else None
        raise UnusableResponse(f"refusal:{category}" if category else "refusal")
    if stop != "end_turn":
        # max_tokens is a truncation; anything else is not a finished answer.
        raise UnusableResponse(str(stop))
    # Integrity failures stay plain ValueErrors: a pinning violation or a response
    # with no ID is a reason to stop the run, not an outcome to record and move past.
    if response.get("model") != spec.model:
        raise ValueError("returned model does not match the pinned request model")
    if not response.get("id") or not isinstance(response.get("usage"), dict):
        raise ValueError("Anthropic response missing ID or usage")
    text = "".join(
        block.get("text", "")
        for block in response.get("content", [])
        if block.get("type") == "text"
    )
    if not text.strip():
        raise UnusableResponse("empty")
    return text, response


def usage(raw: bytes) -> dict | None:
    """Tokens a received response says it consumed, or None if it reports none."""
    try:
        response = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(response, dict) or not isinstance(response.get("usage"), dict):
        return None
    counted = response["usage"]
    try:
        return {
            "input_tokens": int(counted["input_tokens"]),
            "output_tokens": int(counted["output_tokens"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def error_code(raw: bytes) -> str | None:
    try:
        error = json.loads(raw).get("error", {})
    except (ValueError, AttributeError):
        return None
    return error.get("type") if isinstance(error, dict) else None


def retryable(status: int) -> bool:
    # 429 is a rate limit and 529 is overload: both clear on their own.
    # A 400 for an exhausted credit balance, or a 401, does not.
    return status in {429, 529} or status >= 500
