"""The `DIRECTION.md` test table, one test per ratified case.

These are the cases the specification says "should be unit tests before any API
call is made". Every case is derivable by hand from text already in the repo; no
model and no run is involved. Case numbers match the table in `DIRECTION.md`.
"""

import pytest

from simulacria.measurement.direction import (
    Determinacy,
    Modality,
    Part,
    Presence,
    Scope,
    Sign,
    SlotChange,
    UnratifiedDirection,
    classify,
    direction_vector,
    ladder_move,
    Move,
)

D = Determinacy


def sign(change: SlotChange) -> str:
    return classify(change).value


def test_case_1_qualifier_on_exception_specific_to_absent_loosens():
    assert sign(SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.ABSENT)) == "loosening"


def test_case_2_qualifier_on_duty_specific_to_absent_tightens():
    assert sign(SlotChange.qualifier(Part.DUTY, D.SPECIFIC, D.ABSENT)) == "tightening"


def test_case_3_qualifier_on_exception_specific_to_vague_loosens():
    assert sign(SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.VAGUE)) == "loosening"


def test_case_4_qualifier_on_exception_vague_to_absent_loosens():
    assert sign(SlotChange.qualifier(Part.EXCEPTION, D.VAGUE, D.ABSENT)) == "loosening"


def test_case_5_exception_removed_duty_intact_tightens():
    assert sign(SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED)) == "tightening"


def test_case_6_ska_to_bor_on_duty_loosens():
    assert sign(SlotChange.modality(Part.DUTY, Modality.BINDING, Modality.WEAK)) == "loosening"


def test_case_7_actor_narrowed_on_duty_loosens():
    assert sign(SlotChange.actor(Part.DUTY, Scope.NARROWED)) == "loosening"


def test_case_8_pure_rewording_all_slots_intact_is_neutral():
    unchanged = [
        SlotChange.qualifier(Part.DUTY, D.SPECIFIC, D.SPECIFIC),
        SlotChange.qualifier(Part.EXCEPTION, D.VAGUE, D.VAGUE),
        SlotChange.actor(Part.DUTY, Scope.UNCHANGED),
        SlotChange.modality(Part.DUTY, Modality.BINDING, Modality.BINDING),
    ]
    assert all(classify(c) is Sign.NEUTRAL for c in unchanged)
    assert direction_vector(unchanged).as_tuple() == (0, 0, 4)


def test_case_9_qualifier_dropped_and_actor_broadened_is_one_each():
    changes = [
        SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.ABSENT),  # loosening
        SlotChange.actor(Part.DUTY, Scope.BROADENED),  # tightening
    ]
    assert direction_vector(changes).as_tuple() == (1, 1, 0)


def test_case_9b_qualifier_dropped_and_actor_narrowed_is_two_loosenings():
    changes = [
        SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.ABSENT),  # loosening
        SlotChange.actor(Part.DUTY, Scope.NARROWED),  # loosening
    ]
    assert direction_vector(changes).as_tuple() == (0, 2, 0)


def test_case_10_ceiling_removed_permission_intact_loosens():
    assert sign(SlotChange.whole_part(Part.CEILING, Presence.REMOVED)) == "loosening"


def test_case_11_ceiling_weakened_specific_to_vague_loosens():
    assert sign(SlotChange.ceiling_magnitude(D.SPECIFIC, D.VAGUE)) == "loosening"


def test_case_12_ceiling_strengthened_vague_to_specific_tightens():
    assert sign(SlotChange.ceiling_magnitude(D.VAGUE, D.SPECIFIC)) == "tightening"


def test_ceiling_bound_larger_cap_loosens():
    # A bigger cap on a granted power is a weaker ceiling: 6 -> 12 months, or the
    # turordning exemption 2 -> 3 employees, both loosen.
    assert sign(SlotChange.ceiling_bound(6, 12)) == "loosening"
    assert sign(SlotChange.ceiling_bound(2, 3)) == "loosening"


def test_ceiling_bound_smaller_cap_tightens_and_equal_is_neutral():
    assert sign(SlotChange.ceiling_bound(12, 6)) == "tightening"
    assert classify(SlotChange.ceiling_bound(6, 6)) is Sign.NEUTRAL


def test_case_13_qualifier_on_ceiling_specific_to_absent_loosens():
    assert sign(SlotChange.qualifier(Part.CEILING, D.SPECIFIC, D.ABSENT)) == "loosening"


def test_case_14_exception_removal_and_ceiling_removal_must_disagree():
    exception = sign(SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED))
    ceiling = sign(SlotChange.whole_part(Part.CEILING, Presence.REMOVED))
    assert exception == "tightening"
    assert ceiling == "loosening"
    assert exception != ceiling


def test_case_9_never_collapses_to_neutral():
    """The regression test the netting decision exists for: if this ever nets to
    (0, 0, ...) the metric can no longer express the finding the project studies."""
    changes = [
        SlotChange.qualifier(Part.EXCEPTION, D.SPECIFIC, D.ABSENT),
        SlotChange.actor(Part.DUTY, Scope.BROADENED),
    ]
    vector = direction_vector(changes)
    assert vector.tightening and vector.loosening
    assert vector.tightening - vector.loosening == 0  # a net would read "nothing happened"


def test_ladder_move_direction():
    assert ladder_move(D.SPECIFIC, D.ABSENT) is Move.WEAKENED
    assert ladder_move(D.ABSENT, D.SPECIFIC) is Move.STRENGTHENED
    assert ladder_move(D.VAGUE, D.VAGUE) is Move.UNCHANGED


def test_unratified_boundaries_are_reported_not_guessed():
    with pytest.raises(UnratifiedDirection):
        SlotChange.whole_part(Part.DUTY, Presence.REMOVED)
    with pytest.raises(UnratifiedDirection):
        classify(SlotChange.modality(Part.EXCEPTION, Modality.BINDING, Modality.WEAK))
