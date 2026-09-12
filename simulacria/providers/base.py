"""The provider contract, and the errors every provider raises.

The errors live here rather than in one provider because the run logic branches
on them: a transient failure is retried, an unusable response ends one chain, and
anything else stops the run. Those three scopes must mean the same thing
whichever API produced them.
"""

from __future__ import annotations

from types import ModuleType
from typing import Protocol


class RecordedAPIError(ValueError):
    """An HTTP failure whose body is already saved. Carries no provider text.

    `code` is whatever the provider calls the failure; `retryable` is the
    provider's judgement about whether waiting could help.
    """

    def __init__(self, status: int, raw: bytes, code: str | None, retryable: bool):
        self.status = status
        self.code = code
        self.retryable = retryable
        super().__init__(f"API HTTP {status}; see saved raw response")


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
        super().__init__(f"response unusable: {reason}; raw response retained")


class Provider(Protocol):
    """What a provider module must expose. See anthropic.py for the worked case."""

    KEY_VARIABLE: str
    KEY_PREFIX: str

    def accepts_key(self, key: str) -> bool: ...
    def build_payload(self, spec, instructions: str, text: str, max_tokens: int) -> dict: ...
    def with_schema(self, payload: dict, schema: dict) -> dict: ...
    def request_input(self, payload: dict) -> str: ...
    def request_instructions(self, payload: dict) -> str: ...
    def post(self, payload: dict, key: str, timeout: int) -> tuple[int, bytes]: ...
    def decode(self, raw: bytes, spec) -> tuple[str, dict]: ...
    def usage(self, raw: bytes) -> dict | None: ...
    def error_code(self, raw: bytes) -> str | None: ...
    def retryable(self, status: int) -> bool: ...


def get(name: str) -> ModuleType:
    from simulacria.providers import anthropic, openai

    modules = {"anthropic": anthropic, "openai": openai}
    if name not in modules:
        raise ValueError(f"unknown provider {name!r}; available: {sorted(modules)}")
    return modules[name]


def names() -> list[str]:
    return ["anthropic", "openai"]
