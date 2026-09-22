"""The metric. Empty until Phase 2.

`direction.py` and `contracts.py` land here. The rule that makes this a separate
subpackage rather than a naming convention:

    Nothing in this package may import from `simulacria.selection`.

Selection decides what to look at; measurement decides what a change means. A
marker regex or a ranking score reaching into the metric would put a heuristic
where `DIRECTION.md` requires hand-annotated slot state, and it would arrive as
an innocuous-looking import. Here it is a dependency edge between two named
subpackages, visible in review.

Slot state -- which part a qualifier attaches to, its rung on the ladder --
enters this package from the hand-annotated corpus, never from a regex.
"""

from __future__ import annotations

from simulacria.measurement.changes import (
    ChangeOutcome,
    passage_changes,
    passage_vector,
    read_change,
    unobservable_reasons,
)
from simulacria.measurement.direction import (
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
    "passage_changes",
    "passage_vector",
    "read_change",
    "unobservable_reasons",
]
