"""Bridge a blinded slot reading to a `direction` SlotChange.

`direction.py` is pure: it classifies a SlotChange whose rungs are already known.
This module is the honest translation from what a reading actually reports --
`present` / `absent` / `uncertain` and a verbatim quote (see
`measurement.slot_reading`) -- into that input, using the hand-annotated source
slot for the part it attaches to, its kind, and its baseline determinacy or
modality rung.

The comparison is source-anchored: a child reading is compared to the source
slot the corpus annotated, the same grain `reporting.runs.comparison_rows`
already lines up. Insertion of a slot that the source never had is therefore out
of scope here and reported as such, not invented.

What it will not do is guess. A binary present/absent reader cannot see a
`specific -> vague` step on the determinacy ladder (DIRECTION.md), and it cannot
see an actor scope narrowing while the actor is still named. Those return
`observable = False` with a reason, never `neutral`. Calling an unseen weakening
`neutral` would hide exactly the generation this project exists to catch, so the
count vector is built only from observable changes and the unobservable ones are
reported alongside it.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulacria.measurement.direction import (
    Determinacy,
    DirectionVector,
    Modality,
    Part,
    Presence,
    Sign,
    SlotChange,
    classify,
    direction_vector,
)

_LADDER_KINDS = frozenset({"condition", "deadline"})


def _presence(observation: dict) -> str | None:
    """Coarse present/absent from a reading status; None when unresolved.

    `uncertain`, a missing status and `not_read` are all unresolved: a change
    cannot be read off them and must be reported, not treated as absence.
    """
    status = observation.get("status")
    if status in {"present", "absent"}:
        return status
    return None


@dataclass(frozen=True)
class ChangeOutcome:
    """One slot's outcome: either an observable, classified change or a reason it
    could not be read from the current reading."""

    slot_id: str
    kind: str
    part: Part
    observable: bool
    reason: str
    change: SlotChange | None
    sign: Sign | None

    @classmethod
    def unobservable(cls, slot: dict, part: Part, reason: str) -> ChangeOutcome:
        return cls(slot["slot_id"], slot["kind"], part, False, reason, None, None)

    @classmethod
    def observed(cls, slot: dict, part: Part, change: SlotChange) -> ChangeOutcome:
        return cls(slot["slot_id"], slot["kind"], part, True, "computed", change, classify(change))


def _vanished_change(slot: dict, part: Part) -> ChangeOutcome:
    """The slot was present in the source and is absent in the child. This is the
    one determinacy transition a binary reader resolves fully: the rung reached
    is `absent`, and the baseline rung is annotated in the corpus."""
    kind = slot["kind"]
    if kind == "exception":
        return ChangeOutcome.observed(
            slot, part, SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED)
        )
    if kind == "bound":
        # A cap that has vanished entirely is a whole ceiling removed, not a cap
        # merely relaxed; the latter is a determinacy step a binary reader cannot
        # see and is reported unobservable one branch up, like any qualifier.
        return ChangeOutcome.observed(
            slot, part, SlotChange.whole_part(Part.CEILING, Presence.REMOVED)
        )
    if kind in _LADDER_KINDS:
        base = slot.get("determinacy")
        if base not in {"specific", "vague"}:
            return ChangeOutcome.unobservable(slot, part, "no baseline determinacy annotation")
        change = SlotChange.qualifier(part, Determinacy[base.upper()], Determinacy.ABSENT)
        return ChangeOutcome.observed(slot, part, change)
    if kind == "modality":
        base = slot.get("modality")
        if base not in {"binding", "weak"}:
            return ChangeOutcome.unobservable(slot, part, "no baseline modality annotation")
        change = SlotChange.modality(part, Modality[base.upper()], Modality.ABSENT)
        return ChangeOutcome.observed(slot, part, change)
    if kind == "actor":
        # An actor vanishing entirely is not a ratified narrowing/broadening, and
        # scope is not what present/absent reports. Report it, do not sign it.
        return ChangeOutcome.unobservable(
            slot, part, "actor scope is not observable as present/absent"
        )
    return ChangeOutcome.unobservable(slot, part, f"unhandled slot kind {kind!r}")


def read_change(slot: dict, before: dict, after: dict) -> ChangeOutcome:
    """Classify one source slot's change into a child reading, or report why not.

    `slot` is the hand-annotated source slot (kind, attaches_to, baseline rung).
    `before` and `after` are reading observations ({status, quote, ...}); in a
    source-anchored comparison `before` is the source slot's own reading.
    """
    part = Part(slot["attaches_to"])
    b, a = _presence(before), _presence(after)
    if b is None or a is None:
        return ChangeOutcome.unobservable(slot, part, "reading not resolved to present/absent")
    if b == "absent":
        return ChangeOutcome.unobservable(
            slot, part, "baseline slot absent; insertion is out of scope here"
        )
    if a == "present":
        # Still present: a binary reader cannot see a specific -> vague step.
        return ChangeOutcome.unobservable(
            slot, part, "slot still present; determinacy rung not observable"
        )
    return _vanished_change(slot, part)


def passage_changes(
    slots: list[dict], before: dict[str, dict], after: dict[str, dict]
) -> list[ChangeOutcome]:
    """Every source slot's outcome, keyed by slot_id in the two reading maps."""
    return [
        read_change(s, before.get(s["slot_id"], {}), after.get(s["slot_id"], {})) for s in slots
    ]


def passage_vector(outcomes: list[ChangeOutcome]) -> DirectionVector:
    """The count vector over observable changes only. Unobservable slots are not
    folded in as neutral -- see `unobservable_reasons` for what was left out."""
    return direction_vector([o.change for o in outcomes if o.observable and o.change is not None])


def unobservable_reasons(outcomes: list[ChangeOutcome]) -> dict[str, int]:
    """How many slots could not be read, by reason. Reported next to the vector so
    an unseen change is never silently counted as 'nothing happened'."""
    counts: dict[str, int] = {}
    for outcome in outcomes:
        if not outcome.observable:
            counts[outcome.reason] = counts.get(outcome.reason, 0) + 1
    return counts
