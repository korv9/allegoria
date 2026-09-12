"""One module per LLM API. Everything above them sees payloads and raw bytes.

A provider knows four things and nothing else: how to build a request for a
model, how to send it, how to read a response, and how to price the usage it
reports. It does not know what a chain is, what a slot is, or what the budget is
for -- so a second API is a module here, never an edit to the experiment.

Two rules every provider must keep, because the protocol depends on them:

- **The raw bytes are returned untouched.** They are the receipt; anything
  parsed from them must be reproducible from the bytes on disk.
- **No silent substitution.** No client-side retry that hides a paid attempt,
  and no fallback model. A refusal is data; a model that quietly becomes another
  model destroys the only thing a manifest is for.
"""

from __future__ import annotations

from simulacria.providers.base import get, names

__all__ = ["get", "names"]
