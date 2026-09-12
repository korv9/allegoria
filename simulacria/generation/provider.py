"""Model I/O, dispatched by model id. Credentials never enter payloads or errors.

Everything above this module names a model, not an API. The registry
(`configs/models.yaml`) says which provider serves that model, and
`simulacria/providers/` implements each API. Adding a model is a registry entry;
adding an API is a provider module; neither is a change to the experiment.

Call shapes are unchanged from when this was Anthropic-only, so the run code
still sees a payload going in and raw bytes coming out -- and every paid attempt
can still be receipted, hashed and replayed byte-for-byte from disk.
"""

from __future__ import annotations

import os
from pathlib import Path

from simulacria.generation.models import ModelSpec, by_model_id, by_name, defaults, known_model_id
from simulacria.providers import get as provider_for
from simulacria.providers.base import BudgetExceeded, RecordedAPIError, UnusableResponse

__all__ = [
    "BudgetExceeded",
    "ModelSpec",
    "RecordedAPIError",
    "UnusableResponse",
    "api_key",
    "billed_cost",
    "estimated_cost",
    "post_response",
    "request_input",
    "request_instructions",
    "request_payload",
    "response_text",
    "supported",
    "usage_cost",
    "with_schema",
]

REQUEST_TIMEOUT = 300


def spec(model: str | ModelSpec) -> ModelSpec:
    """A spec from a registry name, a wire model id, or a spec that is already one."""
    if isinstance(model, ModelSpec):
        return model
    try:
        return by_name(model)
    except ValueError:
        return by_model_id(model)


def default_spec(role: str) -> ModelSpec:
    return by_name(defaults()[role])


def supported(model_id: str) -> bool:
    """Whether a saved response's model is one this code can still decode."""
    return known_model_id(model_id)


def _read_env_or_dotenv(root: Path, variable: str) -> str:
    key = os.environ.get(variable, "").strip()
    if key:
        return key
    path = root / ".env"
    if not path.is_file():
        return ""
    values = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == variable:
            values.append(value.strip().strip("\"'"))
    if len(values) > 1:
        raise ValueError(f".env contains duplicate {variable} entries")
    return values[0] if values else ""


def api_key(root: Path, model: str | ModelSpec | None = None) -> str:
    """The key for a model's provider, from the environment or the ignored .env.

    Each provider names its own variable and falls back to the shared
    `LLM_API_KEY`, so one key works when only one provider is in use and two
    coexist when they are not. The value is never printed, logged or saved.
    """
    resolved = spec(model) if model is not None else default_spec("transformer")
    module = provider_for(resolved.provider)
    key = _read_env_or_dotenv(root, module.KEY_VARIABLE)
    if not key and module.KEY_VARIABLE != "LLM_API_KEY":
        key = _read_env_or_dotenv(root, "LLM_API_KEY")
    if not module.accepts_key(key):
        variables = module.KEY_VARIABLE
        if module.KEY_VARIABLE != "LLM_API_KEY":
            variables += " (or LLM_API_KEY)"
        raise ValueError(
            f"Set {variables} to an {resolved.provider.capitalize()} key starting "
            f"{module.KEY_PREFIX!r} in the project .env or environment"
        )
    return key


def request_payload(
    model: str | ModelSpec, instructions: str, text: str, max_tokens: int | None = None
) -> dict:
    resolved = spec(model)
    if not instructions.strip() or not text.strip():
        raise ValueError("instructions and input must be nonempty")
    module = provider_for(resolved.provider)
    return module.build_payload(resolved, instructions, text, max_tokens or resolved.max_tokens)


def with_schema(payload: dict, schema: dict) -> dict:
    """Constrain the reply to a JSON schema. Syntax only -- not semantic correctness."""
    resolved = spec(payload["model"])
    if not resolved.structured_output:
        raise ValueError(f"{resolved.name} does not support structured output")
    return provider_for(resolved.provider).with_schema(payload, schema)


def request_input(payload: dict) -> str:
    """The text a request actually sent, for replay checks that must not know the wire shape."""
    return provider_for(spec(payload["model"]).provider).request_input(payload)


def request_instructions(payload: dict) -> str:
    return provider_for(spec(payload["model"]).provider).request_instructions(payload)


def post_response(payload: dict, key: str) -> tuple[int, bytes]:
    """One attempt, returning the status and the exact response bytes."""
    resolved = spec(payload["model"])
    return provider_for(resolved.provider).post(payload, key, REQUEST_TIMEOUT)


def response_text(raw: bytes, requested_model: str | ModelSpec) -> tuple[str, dict]:
    """The answer text and the parsed response, or an error naming which kind it is."""
    resolved = spec(requested_model)
    return provider_for(resolved.provider).decode(raw, resolved)


def recorded_error(status: int, raw: bytes, model: str | ModelSpec) -> RecordedAPIError:
    module = provider_for(spec(model).provider)
    return RecordedAPIError(status, raw, module.error_code(raw), module.retryable(status))


def estimated_cost(payload: dict) -> float:
    """Conservative reservation using UTF-8 bytes plus overhead, not a quote."""
    import json

    resolved = spec(payload["model"])
    input_upper = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 1024
    max_tokens = (
        payload.get("max_tokens") or payload.get("max_output_tokens") or resolved.max_tokens
    )
    return resolved.cost(input_upper, max_tokens)


def usage_cost(response: dict) -> float:
    resolved = spec(response["model"])
    counted = response["usage"]
    return resolved.cost(counted["input_tokens"], counted["output_tokens"])


def billed_cost(raw: bytes, requested_model: str | ModelSpec) -> float:
    """What a received response says was consumed, whatever its outcome.

    Truncated and refused responses carry usage and are billed; a 429 or an
    overload page carries none and is not. Anything unparseable counts as zero,
    because the bytes are retained and an HTML error page must not crash budget
    accounting.
    """
    try:
        resolved = spec(requested_model)
    except ValueError:
        return 0.0
    counted = provider_for(resolved.provider).usage(raw)
    if not counted:
        return 0.0
    return resolved.cost(counted["input_tokens"], counted["output_tokens"])
