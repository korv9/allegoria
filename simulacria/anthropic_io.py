"""Anthropic Messages API I/O. Credentials never enter saved requests or error messages.

The only module that talks to a model provider. Everything else sees a payload
dict going in and raw response bytes coming out, so every paid attempt can be
receipted, hashed and replayed byte-for-byte from disk.

Models are the two cheapest Anthropic offers, at the user's request: they must
differ (PROTOCOL.md, "Separate models"), and reading is the larger share of the
calls, so the cheaper model reads. The earlier selection probe preferred Opus 5
as reader; see predictions/2026-09-11-amendment-cheapest-models.md.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import anthropic

TRANSFORMER = "claude-sonnet-5"
# The dated ID, not the alias: the API answers with the dated ID, and a response
# naming a different model than the request fails the pinning check.
EXTRACTOR = "claude-haiku-4-5-20251001"
# USD per million tokens, input / output. Thinking tokens bill as output.
PRICES = {TRANSFORMER: (2.00, 10.00), EXTRACTOR: (1.00, 5.00)}
# Only models that accept the parameter; Haiku 4.5 rejects `effort` outright.
EFFORT = {TRANSFORMER: "low"}
# Generous on purpose: thinking tokens count against the cap, and a chain that
# dies because a token ceiling truncated it is an artifact, not an outcome.
MAX_TOKENS = 8000
KEY_VARIABLE = "LLM_API_KEY"
# Recorded in every manifest, per model: the two differ in what can be set at all.
# Nothing here is sent except effort; the rest names the defaults that apply.
SAMPLING = {
    TRANSFORMER: {
        "effort": "low",
        "thinking": "adaptive (model default)",
        "temperature": "not settable on this model",
    },
    EXTRACTOR: {
        "effort": "not supported by this model",
        "thinking": "off (model default)",
        "temperature": "API default 1.0, not set in the request",
    },
}


class RecordedAPIError(ValueError):
    """Safe error metadata; raw provider text stays in the recorded response."""

    def __init__(self, status: int, raw: bytes):
        self.status = status
        try:
            error = json.loads(raw).get("error", {})
        except (ValueError, AttributeError):
            error = {}
        self.code = error.get("type") if isinstance(error, dict) else None
        # 429 is a rate limit and 529 is overload: both clear on their own.
        # A 400 for an exhausted credit balance, or a 401, does not.
        self.retryable = status in {429, 529} or status >= 500
        super().__init__(f"Anthropic HTTP {status}; see saved raw response")


class BudgetExceeded(ValueError):
    """The local USD limit would be crossed by this call. Stops a run, never retried."""


class UnusableResponse(ValueError):
    """A received response with no usable text: truncated, refused or empty.

    Distinct from a transport or integrity error. PROTOCOL.md treats refusals and
    truncations as data -- they end the chain they occur in, but they say nothing
    about whether the next chain will work, so they must not stop a run.
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Anthropic response unusable: {reason}; raw response retained")


def api_key(root: Path) -> str:
    key = os.environ.get(KEY_VARIABLE, "").strip()
    if not key:
        path = root / ".env"
        if path.is_file():
            values = []
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                name, sep, value = line.partition("=")
                if sep and name.strip() == KEY_VARIABLE:
                    values.append(value.strip().strip("\"'"))
            if len(values) > 1:
                raise ValueError(f".env contains duplicate {KEY_VARIABLE} entries")
            key = values[0] if values else ""
    if not key.startswith("sk-ant-"):
        raise ValueError(
            f"Set {KEY_VARIABLE} to an Anthropic key in the project .env or environment"
        )
    return key


def supported(model: str) -> bool:
    return model in PRICES


def request_payload(model: str, instructions: str, text: str, max_tokens: int = MAX_TOKENS) -> dict:
    if not supported(model):
        raise ValueError("Use an explicitly supported pinned model")
    if not instructions.strip() or not text.strip():
        raise ValueError("instructions and input must be nonempty")
    # No refusal fallbacks, deliberately: a fallback re-runs a refused request on a
    # different model in silence. A refusal is data, and the model must stay pinned.
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": instructions,
        "messages": [{"role": "user", "content": text}],
    }
    if model in EFFORT:
        payload["output_config"] = {"effort": EFFORT[model]}
    return payload


def with_schema(payload: dict, schema: dict) -> dict:
    """Constrain the reply to a JSON schema. Syntax only -- not semantic correctness."""
    payload["output_config"] = {**payload.get("output_config", {}), "format": schema}
    return payload


def request_input(payload: dict) -> str:
    """The text a request actually sent, for replay checks that must not know the wire shape."""
    return payload["messages"][0]["content"]


def request_instructions(payload: dict) -> str:
    return payload["system"]


@lru_cache(maxsize=4)
def _client(key: str) -> anthropic.Anthropic:
    # max_retries=0: the SDK would otherwise retry 429s out of sight, and every
    # paid attempt must have its own durable receipt.
    return anthropic.Anthropic(api_key=key, max_retries=0, timeout=300)


def post_response(payload: dict, key: str) -> tuple[int, bytes]:
    """One attempt, returning the status and the exact response bytes."""
    try:
        raw = _client(key).messages.with_raw_response.create(**payload)
        return raw.status_code, raw.content
    except anthropic.APIStatusError as error:
        return error.status_code, error.response.content
    except anthropic.APIConnectionError:
        # An OSError, so callers keep the worst-case budget hold: with no response
        # there is no proof the request was not processed and billed. No message
        # text is carried -- transport errors can echo request details.
        raise ConnectionError("Anthropic API unreachable") from None


def response_text(raw: bytes, requested_model: str) -> tuple[str, dict]:
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
    if response.get("model") != requested_model:
        raise ValueError("Returned model does not match pinned request model")
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


def estimated_cost(payload: dict) -> float:
    """Conservative reservation using UTF-8 bytes plus overhead, not a quote."""
    input_rate, output_rate = PRICES[payload["model"]]
    input_upper = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 1024
    return (input_upper * input_rate + payload["max_tokens"] * output_rate) / 1_000_000


def usage_cost(response: dict) -> float:
    input_rate, output_rate = PRICES[response["model"]]
    usage = response["usage"]
    return (usage["input_tokens"] * input_rate + usage["output_tokens"] * output_rate) / 1_000_000


def billed_cost(raw: bytes, requested_model: str) -> float:
    """What a received response says was consumed, whatever its outcome.

    Truncated and refused responses carry usage and are billed; a 429 or an
    overload page carries none and is not. Anything unparseable counts as zero,
    because the bytes are retained and an HTML error page must not crash budget
    accounting.
    """
    try:
        response = json.loads(raw)
    except ValueError:
        return 0.0
    if not isinstance(response, dict) or not isinstance(response.get("usage"), dict):
        return 0.0
    model = response.get("model") if supported(response.get("model", "")) else requested_model
    try:
        return usage_cost({"model": model, "usage": response["usage"]})
    except (KeyError, TypeError):
        return 0.0
