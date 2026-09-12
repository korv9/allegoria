"""OpenAI Responses API. **Unverified: no call has been made through this module.**

It exists so the provider seam has a second implementation and so an OpenAI key
can be used without editing the experiment. It is written from the documented
request and response shape and exercised only by offline fixtures, which is why
every OpenAI entry in `configs/models.yaml` carries `verified: null` and a paid
run refuses them unless you pass `--allow-unverified-model`.

Before trusting it with money, run `scripts/investigations/check_provider.py`:
one cheap live call that checks the response decodes, the model id comes back
pinned, and the usage fields are where this code looks for them.

No SDK: a plain HTTPS request keeps the dependency list short and makes the exact
bytes on the wire obvious, which is what the receipts are about.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from simulacria.providers.base import UnusableResponse

KEY_VARIABLE = "OPENAI_API_KEY"
KEY_PREFIX = "sk-"
ENDPOINT = "https://api.openai.com/v1/responses"


def accepts_key(key: str) -> bool:
    """An Anthropic key also starts with `sk-`; sending it here would leak it."""
    return key.startswith(KEY_PREFIX) and not key.startswith("sk-ant-")


def build_payload(spec, instructions: str, text: str, max_tokens: int) -> dict:
    payload = {
        "model": spec.model,
        "instructions": instructions,
        "input": text,
        "max_output_tokens": max_tokens,
        # No store: a research receipt lives in this repository, not in an
        # account's dashboard where it can be deleted independently.
        "store": False,
    }
    effort = spec.params.get("reasoning_effort")
    if effort:
        payload["reasoning"] = {"effort": effort}
    for key, value in spec.params.items():
        if key != "reasoning_effort":
            payload[key] = value
    return payload


def with_schema(payload: dict, schema: dict) -> dict:
    """Responses API structured output: the schema goes under text.format."""
    inner = schema.get("schema", schema)
    payload["text"] = {
        "format": {"type": "json_schema", "name": "slot_reading", "strict": True, "schema": inner}
    }
    return payload


def request_input(payload: dict) -> str:
    return payload["input"]


def request_instructions(payload: dict) -> str:
    return payload["instructions"]


def post(payload: dict, key: str, timeout: int = 300) -> tuple[int, bytes]:
    """One attempt, returning the status and the exact response bytes."""
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        # A failed call is still evidence: its body is returned for the receipt.
        return error.code, error.read()
    except urllib.error.URLError:
        # No response means no proof it was not processed and billed, so this
        # stays an OSError and the caller keeps its worst-case budget hold.
        raise ConnectionError("OpenAI API unreachable") from None


def decode(raw: bytes, spec) -> tuple[str, dict]:
    response = json.loads(raw)
    status = response.get("status")
    if status == "incomplete":
        details = response.get("incomplete_details") or {}
        raise UnusableResponse(str(details.get("reason") or "incomplete"))
    if status != "completed":
        raise UnusableResponse(str(status))
    if response.get("model") != spec.model:
        raise ValueError("returned model does not match the pinned request model")
    if not response.get("id") or not isinstance(response.get("usage"), dict):
        raise ValueError("OpenAI response missing ID or usage")
    parts = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue  # reasoning items carry no answer text
        for block in item.get("content", []):
            if block.get("type") == "refusal":
                raise UnusableResponse("refusal")
            if block.get("type") == "output_text":
                parts.append(block.get("text", ""))
    text = "".join(parts)
    if not text.strip():
        raise UnusableResponse("empty")
    return text, response


def usage(raw: bytes) -> dict | None:
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
    if not isinstance(error, dict):
        return None
    return error.get("code") or error.get("type")


def retryable(status: int) -> bool:
    # 429 covers both rate limits and an exhausted quota; the quota case is
    # separated by the caller through the recorded error code, not by status.
    return status == 429 or status >= 500
