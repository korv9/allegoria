"""The reading-to-change bridge: what it computes, and what it refuses to guess."""

from pathlib import Path

from simulacria.measurement.changes import (
    passage_changes,
    passage_vector,
    read_change,
    unobservable_reasons,
)
from simulacria.measurement.corpus import load_corpus

ROOT = Path(__file__).resolve().parents[1]

PRESENT = {"status": "present"}
ABSENT = {"status": "absent"}
UNCERTAIN = {"status": "uncertain"}


def qualifier(part, determinacy):
    return {"slot_id": "q", "kind": "condition", "attaches_to": part, "determinacy": determinacy}


def test_exception_removed_is_tightening():
    slot = {"slot_id": "exc", "kind": "exception", "attaches_to": "duty"}
    outcome = read_change(slot, PRESENT, ABSENT)
    assert outcome.observable and outcome.sign.value == "tightening"


def test_qualifier_on_exception_vanishing_loosens():
    outcome = read_change(qualifier("exception", "specific"), PRESENT, ABSENT)
    assert outcome.observable and outcome.sign.value == "loosening"


def test_qualifier_on_duty_vanishing_tightens():
    outcome = read_change(qualifier("duty", "specific"), PRESENT, ABSENT)
    assert outcome.observable and outcome.sign.value == "tightening"


def test_modality_on_duty_vanishing_loosens():
    slot = {"slot_id": "m", "kind": "modality", "attaches_to": "duty", "modality": "binding"}
    outcome = read_change(slot, PRESENT, ABSENT)
    assert outcome.observable and outcome.sign.value == "loosening"


def test_slot_still_present_is_unobservable_not_neutral():
    outcome = read_change(qualifier("exception", "specific"), PRESENT, PRESENT)
    assert not outcome.observable
    assert "determinacy rung not observable" in outcome.reason
    assert outcome.sign is None


def test_uncertain_reading_is_reported_not_absence():
    outcome = read_change(qualifier("duty", "specific"), PRESENT, UNCERTAIN)
    assert not outcome.observable and "not resolved" in outcome.reason


def test_actor_scope_change_is_not_signed():
    slot = {"slot_id": "a", "kind": "actor", "attaches_to": "duty"}
    outcome = read_change(slot, PRESENT, ABSENT)
    assert not outcome.observable and "scope" in outcome.reason


def test_missing_baseline_determinacy_is_unobservable():
    slot = {"slot_id": "q", "kind": "condition", "attaches_to": "duty"}
    outcome = read_change(slot, PRESENT, ABSENT)
    assert not outcome.observable and "determinacy annotation" in outcome.reason


def test_baseline_absent_is_out_of_scope():
    outcome = read_change(qualifier("duty", "specific"), ABSENT, ABSENT)
    assert not outcome.observable and "insertion is out of scope" in outcome.reason


def test_passage_vector_counts_observable_only_and_reports_the_rest():
    slots = [
        {"slot_id": "exc", "kind": "exception", "attaches_to": "duty"},
        qualifier_slot := {
            "slot_id": "cond",
            "kind": "condition",
            "attaches_to": "exception",
            "determinacy": "specific",
        },
        {"slot_id": "kept", "kind": "condition", "attaches_to": "duty", "determinacy": "vague"},
    ]
    before = {s["slot_id"]: PRESENT for s in slots}
    after = {"exc": ABSENT, "cond": ABSENT, "kept": PRESENT}
    outcomes = passage_changes(slots, before, after)
    # exc removed -> tightening, cond on exception vanished -> loosening, kept -> unobservable
    assert passage_vector(outcomes).as_tuple() == (1, 1, 0)
    assert unobservable_reasons(outcomes) == {
        "slot still present; determinacy rung not observable": 1
    }
    assert qualifier_slot["determinacy"] == "specific"


def test_integration_with_real_corpus_when_the_exception_dies():
    sources = load_corpus(ROOT / "corpus/law_probe_v1.yaml", ROOT)
    passage = next(s for s in sources if s["passage_id"] == "sfs-2026-1281:K10P10")
    slots = passage["slots"]
    before = {s["slot_id"]: PRESENT for s in slots}
    # A child in which the deadline qualifier on the exception has vanished, the
    # rest unchanged: the founding "qualifier dies before the exception" shape.
    after = {s["slot_id"]: PRESENT for s in slots}
    after["exception_deadline"] = ABSENT
    outcomes = passage_changes(slots, before, after)
    deadline = next(o for o in outcomes if o.slot_id == "exception_deadline")
    assert deadline.observable and deadline.sign.value == "loosening"
    assert passage_vector(outcomes).as_tuple() == (0, 1, 0)
