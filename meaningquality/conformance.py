"""The conformance suite: the ratified cases every build of the engine must pass.

These are the anchor of `DIRECTION.md` made executable and portable, so a
refactor, a port, or a downstream reuse can prove the engine still classifies the
way the specification says. `python -m meaningquality selftest` runs them.
"""

from __future__ import annotations

from meaningquality.direction import (
    Determinacy as D,
)
from meaningquality.direction import (
    Modality as M,
)
from meaningquality.direction import (
    Part,
    Presence,
    Scope,
    SlotChange,
    classify,
    direction_vector,
)

# (description, change, expected sign)
CASES = [
    (
        "qualifier on exception: specific -> absent",
        SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.ABSENT),
        "loosening",
    ),
    (
        "qualifier on duty: specific -> absent",
        SlotChange.qualifier(Part.DUTY, D.SPECIFIC, D.ABSENT),
        "tightening",
    ),
    (
        "exception removed, duty intact",
        SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED),
        "tightening",
    ),
    ("ska -> bör on the duty", SlotChange.modality(Part.DUTY, M.BINDING, M.WEAK), "loosening"),
    ("actor narrowed on the duty", SlotChange.actor(Part.DUTY, Scope.NARROWED), "loosening"),
    (
        "ceiling removed, permission intact",
        SlotChange.whole_part(Part.CEILING, Presence.REMOVED),
        "loosening",
    ),
    (
        "ceiling weakened: specific -> vague",
        SlotChange.ceiling_magnitude(D.SPECIFIC, D.VAGUE),
        "loosening",
    ),
    (
        "qualifier on a ceiling: specific -> absent",
        SlotChange.qualifier(Part.CEILING, D.SPECIFIC, D.ABSENT),
        "loosening",
    ),
    ("ceiling cap 6 -> 12 (larger cap)", SlotChange.ceiling_bound(6, 12), "loosening"),
    ("ceiling cap 12 -> 6 (smaller cap)", SlotChange.ceiling_bound(12, 6), "tightening"),
]


def run() -> tuple[int, int, list[tuple[str, str, str]]]:
    """Return (passed, total, failures) where each failure is (desc, expected, got)."""
    failures = []
    for desc, change, expected in CASES:
        got = classify(change).value
        if got != expected:
            failures.append((desc, expected, got))
    # Case 9: a dropped qualifier on an exception and a broadened actor on the duty
    # must count as one loosening and one tightening, never net to neutral.
    vector = direction_vector(
        [
            SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.ABSENT),
            SlotChange.actor(Part.DUTY, Scope.BROADENED),
        ]
    )
    if vector.as_tuple() != (1, 1, 0):
        failures.append(("case 9 vector not (1,1,0)", "(1, 1, 0)", str(vector.as_tuple())))
    total = len(CASES) + 1
    return total - len(failures), total, failures
