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
)

_LADDER_KINDS = frozenset({"condition", "deadline"})
_DETERMINACY = {
    "specific": Determinacy.SPECIFIC,
    "vague": Determinacy.VAGUE,
    "absent": Determinacy.ABSENT,
}
_MODALITY = {"binding": Modality.BINDING, "weak": Modality.WEAK, "absent": Modality.ABSENT}


def _rung_change(slot: dict, part: Part, after: dict) -> ChangeOutcome:
    """The slot is still present. If the reading also reports the observed rung
    (a determinacy-aware reading), classify the ladder move -- an unchanged rung
    is a certified `neutral`, a softened one a real weakening. If it reports only
    present/absent (a binary reading), the rung is not observable and is reported,
    never guessed as neutral."""
    kind = slot["kind"]
    if kind == "exception":
        # Present in both: the whole carve-out is intact, no removal. Neutral.
        return ChangeOutcome.neutral(slot, part, "exception intact")
    if kind in _LADDER_KINDS or kind == "bound":
        observed = _DETERMINACY.get(after.get("determinacy"))
        base = _DETERMINACY.get(slot.get("determinacy"))
        if observed is None:
            return ChangeOutcome.unobservable(
                slot, part, "slot still present; determinacy rung not observable"
            )
        if base is None:
            return ChangeOutcome.unobservable(slot, part, "no baseline determinacy annotation")
        change = (
            SlotChange.ceiling_magnitude(base, observed)
            if kind == "bound"
            else SlotChange.qualifier(part, base, observed)
        )
        return ChangeOutcome.observed(slot, part, change)
    if kind == "modality":
        observed = _MODALITY.get(after.get("modality"))
        base = _MODALITY.get(slot.get("modality"))
        if observed is None:
            return ChangeOutcome.unobservable(
                slot, part, "slot still present; modality rung not observable"
            )
        if base is None:
            return ChangeOutcome.unobservable(slot, part, "no baseline modality annotation")
        if part is not Part.DUTY:
            return ChangeOutcome.unobservable(
                slot, part, "modality off the duty has no ratified sign"
            )
        return ChangeOutcome.observed(slot, part, SlotChange.modality(part, base, observed))
    return ChangeOutcome.unobservable(slot, part, "slot still present; change not observable")


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

    @classmethod
    def neutral(cls, slot: dict, part: Part, reason: str) -> ChangeOutcome:
        """An observable non-change: a whole part still present, no removal. It
        counts as neutral, distinct from a rung the reader simply could not see."""
        return cls(slot["slot_id"], slot["kind"], part, True, reason, None, Sign.NEUTRAL)


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
        # Still present: classify the rung move if the reading reports it, else
        # report it unobservable -- a binary reader cannot see a specific -> vague step.
        return _rung_change(slot, part, after)
    return _vanished_change(slot, part)


_PART_KIND = {"exception": Part.EXCEPTION, "bound": Part.CEILING}


def _removed_parts(slots: list[dict], outcomes: list[ChangeOutcome]) -> set[Part]:
    """Parts whose whole-part slot vanished, so their dependent qualifiers are gone
    by consequence, not by an independent weakening of their own."""
    return {
        _PART_KIND[s["kind"]]
        for s, o in zip(slots, outcomes)
        if s["kind"] in _PART_KIND
        and o.change is not None
        and o.change.presence is Presence.REMOVED
    }


def passage_changes(
    slots: list[dict], before: dict[str, dict], after: dict[str, dict]
) -> list[ChangeOutcome]:
    """Every source slot's outcome, keyed by slot_id in the two reading maps.

    When a whole exception or ceiling is removed, a qualifier that hung on it is
    absent as a consequence, not as its own change. Counting it separately would
    turn one whole-part event (case 5/10 in DIRECTION.md) into a contradictory
    vector, so such a qualifier is subsumed and reported, never double-counted.
    """
    outcomes = [
        read_change(s, before.get(s["slot_id"], {}), after.get(s["slot_id"], {})) for s in slots
    ]
    removed = _removed_parts(slots, outcomes)
    if not removed:
        return outcomes
    adjusted = []
    for slot, outcome in zip(slots, outcomes):
        dependent = slot["kind"] not in _PART_KIND and Part(slot["attaches_to"]) in removed
        if dependent:
            part = Part(slot["attaches_to"]).value
            adjusted.append(
                ChangeOutcome.unobservable(
                    slot, Part(slot["attaches_to"]), f"parent {part} removed; subsumed"
                )
            )
        else:
            adjusted.append(outcome)
    return adjusted


def passage_vector(outcomes: list[ChangeOutcome]) -> DirectionVector:
    """The count vector over observable slots only. Unobservable slots are not
    folded in as neutral -- see `unobservable_reasons` for what was left out."""
    signs = [o.sign for o in outcomes if o.observable and o.sign is not None]
    return DirectionVector(
        tightening=sum(s is Sign.TIGHTENING for s in signs),
        loosening=sum(s is Sign.LOOSENING for s in signs),
        neutral=sum(s is Sign.NEUTRAL for s in signs),
    )


def unobservable_reasons(outcomes: list[ChangeOutcome]) -> dict[str, int]:
    """How many slots could not be read, by reason. Reported next to the vector so
    an unseen change is never silently counted as 'nothing happened'."""
    counts: dict[str, int] = {}
    for outcome in outcomes:
        if not outcome.observable:
            counts[outcome.reason] = counts.get(outcome.reason, 0) + 1
    return counts
