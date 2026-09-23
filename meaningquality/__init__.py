"""meaningquality -- a signed, deterministic meaning-quality metric.

Given a source rule's slots and a reading of a derivative (a rewrite, a
description, or a later version), it says per slot whether the norm **loosened**
(permitted world-states grow) or **tightened** (they shrink), reported as a
non-netted count vector. Pure, deterministic, standard library only: no model,
no network. The specification is `DIRECTION.md`; the conformance suite is
`meaningquality.conformance`.

The reusable seam is the reader: text never enters the engine, slot observations
do. Any reader (human annotation, a lexical marker screen, an LLM extractor) that
produces `{slot_id: {status, quote, ...}}` plugs into `measure`.
"""

from __future__ import annotations

from meaningquality import readers
from meaningquality.changes import (
    ChangeOutcome,
    passage_changes,
    passage_vector,
    read_change,
    unobservable_reasons,
)
from meaningquality.direction import (
    Determinacy,
    DirectionVector,
    Modality,
    Move,
    Part,
    Presence,
    Scope,
    Sign,
    SlotChange,
    UnratifiedDirection,
    classify,
    direction_vector,
    ladder_move,
)

__version__ = "0.1.0"


def measure(source_slots: list[dict], before: dict, after: dict) -> dict:
    """Compare a reading of a derivative (`after`) to the source (`before`) over
    the source's slots. Returns the count vector, the per-slot outcomes and the
    reasons any slot was unobservable -- an unseen change is never a silent zero."""
    outcomes = passage_changes(source_slots, before, after)
    return {
        "vector": passage_vector(outcomes).as_tuple(),
        "outcomes": outcomes,
        "unobservable": unobservable_reasons(outcomes),
    }


__all__ = [
    "ChangeOutcome",
    "Determinacy",
    "DirectionVector",
    "Modality",
    "Move",
    "Part",
    "Presence",
    "Scope",
    "Sign",
    "SlotChange",
    "UnratifiedDirection",
    "classify",
    "direction_vector",
    "ladder_move",
    "measure",
    "passage_changes",
    "passage_vector",
    "read_change",
    "readers",
    "unobservable_reasons",
]
