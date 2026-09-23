"""Deterministic `direction` classification. No model judges this; code does.

This implements the ratified derivation rule in `DIRECTION.md` (DD051/DD052).
Read that file before touching anything here. The one definition everything
below is a consequence of:

    Loosening = the set of permitted world-states grows.
    Tightening = it shrinks.

Nothing in this module parses Swedish or inspects raw text. It consumes slot
*states* -- which part a slot attaches to, and its rung on a ladder -- that come
from the hand-annotated corpus and the blinded reading, never from a regex or a
marker score. A slot change is turned into a ternary sign; a passage is a count
vector over its slots, never a net. See `DIRECTION.md` "Reporting shape".

Where `DIRECTION.md` leaves a boundary case unratified, the corresponding call
raises `UnratifiedDirection` rather than inventing a sign. That is the
specification's instruction to the implementer: report ambiguity, do not resolve
it here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Sign(str, Enum):
    """The ternary per-slot result. Never a continuous scale (DIRECTION.md)."""

    TIGHTENING = "tightening"
    LOOSENING = "loosening"
    NEUTRAL = "neutral"


class Part(str, Enum):
    """Which of the four moving parts a slot attaches to. `qualifier` is not a
    part -- it is any slot that hangs on one of these."""

    DUTY = "duty"
    EXCEPTION = "exception"
    CEILING = "ceiling"


class Determinacy(IntEnum):
    """The determinacy ladder. Moving down is `weakened`, up is `strengthened`."""

    ABSENT = 0
    VAGUE = 1
    SPECIFIC = 2


class Modality(IntEnum):
    """Deontic force of the operator itself. `ska`/`får inte` bind; `bör` is weak.

    The lexical mapping (which Swedish word is which rung) belongs to the corpus
    and the reading, not here. This module only compares rungs.
    """

    ABSENT = 0
    WEAK = 1
    BINDING = 2


class Scope(str, Enum):
    """How an actor or applicability slot changed. Breadth has no absolute rung,
    so the relation itself is the datum, not a pair of levels."""

    NARROWED = "narrowed"
    BROADENED = "broadened"
    UNCHANGED = "unchanged"


class Presence(str, Enum):
    """A whole part appearing or disappearing between parent and child."""

    REMOVED = "removed"
    INSERTED = "inserted"


class Move(str, Enum):
    """The result of comparing two ladder rungs."""

    WEAKENED = "weakened"
    STRENGTHENED = "strengthened"
    UNCHANGED = "unchanged"


class UnratifiedDirection(Exception):
    """Raised for a structural position `DIRECTION.md` has not ratified a sign for.

    Per the specification: "Any ambiguity encountered while encoding the table
    must be reported rather than resolved by the implementer."
    """


def ladder_move(before: IntEnum, after: IntEnum) -> Move:
    """Compare two rungs on the same ladder (determinacy or modality)."""
    if type(before) is not type(after):
        raise TypeError("cannot compare rungs from different ladders")
    if after < before:
        return Move.WEAKENED
    if after > before:
        return Move.STRENGTHENED
    return Move.UNCHANGED


def _binding_part(part: Part) -> bool:
    """A duty is binding; an exception and a ceiling are enabling for the purpose
    of the qualifier derivation rule. See the DIRECTION.md derivation table.

    A duty whose own modality is enabling (a bare `får`-duty) is an unratified
    boundary the table does not cover; the corpus does not yet carry that state,
    and inventing its sign here is exactly what the specification forbids.
    """
    return part is Part.DUTY


@dataclass(frozen=True)
class SlotChange:
    """One annotated slot's transition between a parent text and its child.

    Build these with the classmethods rather than the raw constructor: each
    factory encodes which fields a given kind of change is allowed to carry, so
    an ill-formed change cannot be represented.
    """

    kind: str
    part: Part
    move: Move | None = None
    scope: Scope | None = None
    presence: Presence | None = None

    @classmethod
    def qualifier(cls, part: Part, before: Determinacy, after: Determinacy) -> SlotChange:
        """A condition or deadline hanging on a part, moving on the ladder."""
        return cls(kind="condition", part=part, move=ladder_move(before, after))

    @classmethod
    def ceiling_magnitude(cls, before: Determinacy, after: Determinacy) -> SlotChange:
        """The cap of a ceiling itself getting looser or tighter (kind `bound`)."""
        return cls(kind="bound", part=Part.CEILING, move=ladder_move(before, after))

    @classmethod
    def ceiling_bound(cls, before: float, after: float) -> SlotChange:
        """A numeric cap on a granted power changing size. A larger cap (e.g. a
        probation of 6 -> 12 months, or 2 -> 3 employees exempted from a duty) is a
        WEAKER ceiling -- more permitted extent -- so it loosens; a smaller cap
        tightens. This is the magnitude the determinacy ladder alone cannot express.

        Only defined for a ceiling. A magnitude on a duty (a longer deadline to
        comply, a higher threshold to qualify) is part-dependent and not ratified
        here; encode those as determinacy or report the ambiguity.
        """
        if after > before:
            move = Move.WEAKENED
        elif after < before:
            move = Move.STRENGTHENED
        else:
            move = Move.UNCHANGED
        return cls(kind="bound", part=Part.CEILING, move=move)

    @classmethod
    def modality(cls, part: Part, before: Modality, after: Modality) -> SlotChange:
        """The deontic operator of a part changing force (e.g. `ska` -> `bör`)."""
        return cls(kind="modality", part=part, move=ladder_move(before, after))

    @classmethod
    def actor(cls, part: Part, scope: Scope) -> SlotChange:
        """The set of actors the part governs widening or narrowing."""
        return cls(kind="actor", part=part, scope=scope)

    @classmethod
    def whole_part(cls, part: Part, presence: Presence) -> SlotChange:
        """A whole exception or ceiling appearing or disappearing."""
        if part is Part.DUTY:
            raise UnratifiedDirection("whole-duty insertion/removal has no ratified sign")
        return cls(kind="part", part=part, presence=presence)


def _qualifier_sign(part: Part, move: Move) -> Sign:
    """Derivation table, qualifier rows.

    Binding part: weakening the condition makes the duty apply more broadly
    (tightening). Enabling part (exception/ceiling): weakening the condition
    makes the escape hatch or the cap easier to reach (loosening).
    """
    if move is Move.UNCHANGED:
        return Sign.NEUTRAL
    weakened = move is Move.WEAKENED
    if _binding_part(part):
        return Sign.TIGHTENING if weakened else Sign.LOOSENING
    return Sign.LOOSENING if weakened else Sign.TIGHTENING


def _bound_sign(move: Move) -> Sign:
    """A ceiling's own cap. Weakening the cap widens the permission (loosening);
    the enabling-row polarity, which is why a ceiling is not filed under duty."""
    if move is Move.UNCHANGED:
        return Sign.NEUTRAL
    return Sign.LOOSENING if move is Move.WEAKENED else Sign.TIGHTENING


def _modality_sign(part: Part, move: Move) -> Sign:
    """`ska` -> `bör` drains the duty's force, so the duty binds less and
    permitted world-states grow (loosening). Only ratified for the duty; the
    force of an exception's or a ceiling's own operator is not in the table."""
    if move is Move.UNCHANGED:
        return Sign.NEUTRAL
    if part is not Part.DUTY:
        raise UnratifiedDirection("modality change off the duty has no ratified sign")
    return Sign.LOOSENING if move is Move.WEAKENED else Sign.TIGHTENING


def _actor_sign(part: Part, scope: Scope) -> Sign:
    """Narrowing the actors bound by a duty releases parties, so permitted
    world-states grow (loosening); broadening binds more (tightening). On an
    exception the escape hatch itself shrinks or grows, so the polarity flips.
    Both follow directly from the one definition; only the duty case is pinned
    by a test (DIRECTION.md cases 7, 9)."""
    if scope is Scope.UNCHANGED:
        return Sign.NEUTRAL
    narrowed = scope is Scope.NARROWED
    if part is Part.DUTY:
        return Sign.LOOSENING if narrowed else Sign.TIGHTENING
    return Sign.TIGHTENING if narrowed else Sign.LOOSENING


_WHOLE_PART: dict[tuple[Part, Presence], Sign] = {
    (Part.EXCEPTION, Presence.REMOVED): Sign.TIGHTENING,
    (Part.EXCEPTION, Presence.INSERTED): Sign.LOOSENING,
    (Part.CEILING, Presence.REMOVED): Sign.LOOSENING,
    (Part.CEILING, Presence.INSERTED): Sign.TIGHTENING,
}


def classify(change: SlotChange) -> Sign:
    """The sign of one slot change. Pure; the same input always maps here."""
    if change.kind == "part":
        assert change.presence is not None
        return _WHOLE_PART[(change.part, change.presence)]
    if change.kind == "actor":
        assert change.scope is not None
        return _actor_sign(change.part, change.scope)
    if change.kind == "modality":
        assert change.move is not None
        return _modality_sign(change.part, change.move)
    if change.kind == "bound":
        assert change.move is not None
        return _bound_sign(change.move)
    if change.kind == "condition":
        assert change.move is not None
        return _qualifier_sign(change.part, change.move)
    raise ValueError(f"unknown slot change kind: {change.kind!r}")


@dataclass(frozen=True)
class DirectionVector:
    """A passage's direction as a count vector, never a net (DIRECTION.md).

    The headline curve is `loosening` per generation; `tightening` is reported
    alongside, never subtracted, because a fidelity error and a safety error are
    not mirror images.
    """

    tightening: int
    loosening: int
    neutral: int

    def as_tuple(self) -> tuple[int, int, int]:
        """`(n_tightening, n_loosening, n_neutral)` -- the reporting order."""
        return (self.tightening, self.loosening, self.neutral)


def direction_vector(changes: list[SlotChange]) -> DirectionVector:
    """Classify every slot change in a passage and count the signs. No netting:
    a loosening and a tightening in the same passage stay two separate counts."""
    signs = [classify(c) for c in changes]
    return DirectionVector(
        tightening=sum(s is Sign.TIGHTENING for s in signs),
        loosening=sum(s is Sign.LOOSENING for s in signs),
        neutral=sum(s is Sign.NEUTRAL for s in signs),
    )


__all__ = [
    "Sign",
    "Part",
    "Determinacy",
    "Modality",
    "Scope",
    "Presence",
    "Move",
    "UnratifiedDirection",
    "ladder_move",
    "SlotChange",
    "classify",
    "DirectionVector",
    "direction_vector",
]
