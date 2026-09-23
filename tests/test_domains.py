"""The domain contract: a new dataset must be an adapter plus a config, nothing else.

These tests exist to keep the seam from closing again. If the pipeline starts
assuming Swedish statute somewhere -- an id format, a bronze path, a question in
Python -- one of them fails.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from simulacria.domains import get, names
from simulacria.domains.base import ATTACHMENTS, SLOT_KINDS
from simulacria.domains.rfc import sections
from simulacria.generation.plan import load_config, plan
from simulacria.measurement.corpus import load_corpus
from simulacria.measurement.slot_reading import reading_input

ROOT = Path(__file__).resolve().parents[1]


def test_every_shipped_domain_is_registered_and_describes_itself():
    assert set(names()) == {"inline", "rfc", "sfs"}
    for name in names():
        domain = get(name)
        assert domain.language and domain.id_format and callable(domain.resolve)


def test_slot_vocabulary_carries_the_ratified_ceiling_category():
    # DIRECTION.md (DD051/DD052) ratified `ceiling`/`bound`; the shared slot
    # vocabulary must let a corpus express it, or a cap has nowhere to live but
    # `exception`, where its sign flips on removal.
    assert "bound" in SLOT_KINDS
    assert "ceiling" in ATTACHMENTS


def test_unknown_domain_names_itself_rather_than_failing_obscurely():
    with pytest.raises(ValueError, match="unknown corpus domain"):
        get("insurance-policies-we-have-not-written-yet")


@pytest.mark.parametrize(
    ("corpus", "domain", "passages", "language"),
    [
        ("corpus/law_probe_v1.yaml", "sfs", 3, "sv"),
        ("corpus/philosophy_v1.yaml", "inline", 30, "any"),
        ("corpus/rfc_probe_v1.yaml", "rfc", 3, "en"),
    ],
)
def test_shipped_corpora_load_with_verified_lineage(corpus, domain, passages, language):
    rows = load_corpus(ROOT / corpus, ROOT)
    assert len(rows) == passages
    assert {r["domain"] for r in rows} == {domain}
    assert {r["language"] for r in rows} == {language}
    for row in rows:
        assert row["text"].strip() and row["source_url"]
        assert row["text_sha256"] == sha256(row["text"].encode("utf-8")).hexdigest()
        # Every anchored slot quotes its own passage, exactly once.
        for slot in row["slots"]:
            assert slot["question"].strip()
            if slot["quote"] is not None:
                assert row["text"].count(slot["quote"]) == 1


def test_reading_asks_the_corpus_question_in_the_corpus_language():
    english = load_corpus(ROOT / "corpus/rfc_probe_v1.yaml", ROOT)[0]
    asked = json.loads(reading_input(english["text"], english["slots"]))
    assert set(asked) == {"text", "schema"}
    assert [row["question"] for row in asked["schema"]] == [s["question"] for s in english["slots"]]
    assert all("Does the text" in row["question"] for row in asked["schema"])
    # Blinding is domain-independent: the annotation never travels with the text.
    # (The quotes themselves are spans of that text, so they are necessarily in it.)
    assert all(set(row) == {"slot_id", "question"} for row in asked["schema"])


def test_rfc_sections_drop_page_furniture_and_keep_the_heading_line():
    text = (
        "1.  Introduction\n\n   A duty.\n\fFoo [Page 1]\n"
        "RFC 6265             HTTP State Management Mechanism          April 2011\n"
        "\n   Continued.\n\n2.  Next\n\n   Other.\n"
    )
    found = sections(text)
    assert set(found) == {"1", "2"}
    assert found["1"]["text"].startswith("1.  Introduction")
    assert "Page 1" not in found["1"]["text"]
    assert "HTTP State Management Mechanism" not in found["1"]["text"]
    assert "Continued." in found["1"]["text"]


def test_a_second_domain_needs_no_change_to_the_experiment_engine():
    """The RFC experiment plans from config alone, with the same code path as Swedish."""
    config = load_config(ROOT, "configs/rfc-en.yaml")
    sources, chains = plan(ROOT, config)
    assert len(sources) == 3
    assert len(chains) == 24  # three sections, four styles, two variants
    assert {s["language"] for s in sources} == {"en"}
    assert all(c["instruction"].strip() for c in chains)


def test_corpus_rejects_a_slot_kind_it_does_not_know(tmp_path):
    text = "a duty"
    (tmp_path / "bad.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "domain": "inline",
                "annotation_status": "assistant_draft_requires_human_review",
                "passages": [
                    {
                        "passage_id": "x",
                        "text": text,
                        "text_sha256": sha256(text.encode()).hexdigest(),
                        "slots": [
                            {
                                "slot_id": "s",
                                "kind": "vibe",
                                "attaches_to": "duty",
                                "question": "?",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown slot kind"):
        load_corpus(tmp_path / "bad.yaml", tmp_path)
