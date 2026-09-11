"""Source integrity and honest reporting of failed normative-axis controls."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from simulacria.selection.axis import (
    expectation_checks,
    hit_summary,
    load_corpus,
    match_statutes,
    paired_lengths,
    verify_statutory_snapshot,
    virtue_failures,
)
from simulacria.selection.highlight import marker_spans

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def philosophy():
    return load_corpus(ROOT / "corpus/philosophy_v1.yaml")


def test_corpus_pairs_and_swedish_integrity(philosophy):
    assert len(philosophy) == 30
    assert all(
        sum(r["group"] == g for r in philosophy) == 10
        for g in ("virtue", "categorical", "conditional")
    )
    assert all("?" not in r["text"] and "\ufffd" not in r["text"] for r in philosophy)
    assert "löfte" in philosophy[10]["text"]
    assert max(abs(p["difference"]) for p in paired_lengths(philosophy)) <= 10
    for p in paired_lengths(philosophy):
        pair = [r for r in philosophy if r["pair_id"] == p["pair_id"]]
        assert pair[0]["text"].split("Detta gäller")[0] == pair[1]["text"].split("Detta gäller")[0]


@pytest.mark.parametrize("mutation", ["text", "duplicate", "source", "group", "schema"])
def test_loader_rejects_corrupt_input(tmp_path, philosophy, mutation):
    data = {"schema_version": 1, "passages": deepcopy(philosophy)}
    if mutation == "text":
        data["passages"][0]["text"] += " changed"
    elif mutation == "duplicate":
        data["passages"].append(data["passages"][0])
    elif mutation == "schema":
        data["schema_version"] = 9
    else:
        data["passages"][0][mutation] = "" if mutation == "source" else "unknown"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_corpus(path)


def test_missing_control_is_not_silently_discarded(philosophy):
    with pytest.raises(ValueError, match="incomplete pair"):
        paired_lengths(philosophy[:-1])


def test_snapshot_provenance_and_matching(philosophy):
    baseline = load_corpus(ROOT / "corpus/statutory_axis_v1.yaml")
    assert len(verify_statutory_snapshot(baseline, ROOT)) == 20
    matched = match_statutes(philosophy, baseline)
    assert len({r["passage_id"] for r in matched}) == 10
    assert matched == match_statutes(list(reversed(philosophy)), list(reversed(baseline)))
    with pytest.raises(ValueError, match="not enough"):
        match_statutes(philosophy, baseline[:2])
    corrupted = deepcopy(baseline)
    corrupted[0]["text"] += " changed"
    corrupted[0]["text_sha256"] = sha256(corrupted[0]["text"].encode()).hexdigest()
    with pytest.raises(ValueError, match="text mismatch"):
        verify_statutory_snapshot(corrupted, ROOT)


def test_real_false_positives_remain_visible(philosophy):
    failures = virtue_failures(philosophy)
    assert [r["passage_id"] for r in failures] == ["virtue-09"]
    assert failures[0]["hits"][0]["span"] == "om"
    categorical = [r for r in expectation_checks(philosophy) if r["group"] == "categorical"]
    assert all(not r["pass"] for r in categorical)
    for row in philosophy:
        for hit in marker_spans(row["text"]):
            assert row["text"][hit["start"] : hit["end"]] == hit["span"]
    totals = {r["group"]: r for r in hit_summary(philosophy)}
    assert totals["conditional"]["exception"] == 20
    assert totals["conditional"]["passages_with_exception"] == 10
