"""The engine as a standalone package: it imports, its conformance suite passes,
and its public API and readers behave."""

from meaningquality import Part, Presence, SlotChange, classify, measure
from meaningquality.conformance import run
from meaningquality.readers import VerbatimReader, annotation_reader


def test_conformance_suite_passes():
    passed, total, failures = run()
    assert passed == total, failures


def test_public_api_classifies():
    assert classify(SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED)).value == "tightening"
    assert classify(SlotChange.ceiling_bound(6, 12)).value == "loosening"


def test_measure_signs_a_softened_cap():
    source = [{"slot_id": "cap", "kind": "bound", "attaches_to": "ceiling", "determinacy": "specific"}]
    before = {"cap": {"status": "present", "determinacy": "specific"}}
    after = {"cap": {"status": "present", "determinacy": "vague"}}
    assert measure(source, before, after)["vector"] == (0, 1, 0)


def test_verbatim_reader_detects_survival():
    slots = [{"slot_id": "x", "quote": "högst sex månader"}]
    reader = VerbatimReader()
    assert reader.read("prövotid om högst sex månader", slots)["x"]["status"] == "present"
    assert reader.read("ingen bortre gräns", slots)["x"]["status"] == "absent"


def test_annotation_reader_passthrough():
    readings = {"a": {"status": "present"}}
    assert annotation_reader(readings) == readings
