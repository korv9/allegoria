"""The contract every corpus adapter implements, and the registry that finds them.

A domain answers one question: given a passage id and the repository root, what
is the text, and how is that text tied back to original bytes? Everything the
experiment does afterwards -- budgets, receipts, chains, blinded slot readings,
the DuckDB projection -- is the same whatever the answer was.

Keeping the contract this small is deliberate. A domain that could also change
how slots are validated, or how a reading is judged, would let a dataset quietly
redefine the instrument, and results from two corpora would stop being
comparable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# Slot vocabulary. Shared by every domain on purpose: a corpus may not invent a
# kind, because `attaches_to` is what decides the sign of a direction change.
#
# `bound` and `ceiling` carry the ratified ceiling category (DIRECTION.md,
# DD051/DD052): a `bound` slot is a cap on how far a granted power reaches, and
# `ceiling` is the part a slot hangs on. They matter because removing a ceiling
# loosens where removing an exception tightens, so filing a cap under `exception`
# flips the sign the moment it disappears -- the generation the experiment watches.
SLOT_KINDS = frozenset({"modality", "actor", "condition", "deadline", "exception", "bound"})
ATTACHMENTS = frozenset({"duty", "exception", "ceiling"})


@dataclass(frozen=True)
class PassageSource:
    """One passage's text plus the lineage that proves where it came from."""

    text: str
    document_title: str
    source_url: str
    # None only for text that has no upstream artifact: an inline corpus is its
    # own source, and says so rather than inventing a hash of something else.
    source_sha256: str | None = None


@dataclass(frozen=True)
class Domain:
    """One corpus family: statute, RFC, inline specimens, an insurance policy."""

    name: str
    language: str
    # Human-readable statement of what a passage id means in this domain, shown
    # in error messages when one does not resolve.
    id_format: str
    resolve: Callable[[str, Path, dict], PassageSource]
    # Set when the domain reads bytes committed under data/, for the data map.
    source_dir: str | None = None
    bronze_dir: str | None = None
    notes: str = field(default="")


_REGISTRY: dict[str, Domain] = {}


def register(domain: Domain) -> Domain:
    if domain.name in _REGISTRY:
        raise ValueError(f"domain already registered: {domain.name}")
    _REGISTRY[domain.name] = domain
    return domain


def get(name: str) -> Domain:
    # Import for effect: each module registers itself when first imported.
    from simulacria.domains import inline, rfc, sfs  # noqa: F401

    if name not in _REGISTRY:
        raise ValueError(f"unknown corpus domain {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def names() -> list[str]:
    from simulacria.domains import inline, rfc, sfs  # noqa: F401

    return sorted(_REGISTRY)
