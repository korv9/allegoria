"""Behavioural guards for the small selection cleanup."""

import re

from simulacria.pipeline.tables import marker_hit_rows, provision_rows
from simulacria.selection.determinacy import qualifier_spans, qualifier_spans_with_offsets
from simulacria.selection.highlight import marker_spans
from simulacria.selection.markers import EXCEPTION_MARKERS
from simulacria.selection.shortlist import score_breakdown, score_provision


def test_span_api_preserves_overlapping_quotes():
    text = "Avvikelse får göras endast om behov finns, under förutsättning att vila ges."
    assert qualifier_spans(text) == [r[1] for r in qualifier_spans_with_offsets(text)]
    assert all(
        text[start:end] == quote for _, quote, start, end in qualifier_spans_with_offsets(text)
    )


def test_override_does_not_mutate_production_markers():
    text = "Arbetsgivaren ska ge vila. Undantag gäller om hinder finns."
    before = score_provision(text)
    assert before["score"] == score_breakdown(text)["total"]
    alternative = [("never", re.compile(r"(?!)"), 1)]
    assert score_provision(text, exception_markers=alternative) is None
    assert score_provision(text) == before
    assert any(label == "undantag" for label, *_ in EXCEPTION_MARKERS)


def test_table_hits_and_rendered_hits_agree():
    text = "Arbetsgivaren ska dock inte neka vila om hinder finns."
    rows = marker_hit_rows([{"provision_id": "example", "text": text}])
    expected = {
        ("example", h["category"], h["marker"], h["span"], h["start"]) for h in marker_spans(text)
    }
    assert set(rows) == expected


def test_null_document_version_stays_null():
    row = dict.fromkeys(
        (
            "provision_id",
            "document_id",
            "document_title",
            "kind",
            "chapter",
            "label",
            "heading",
            "text",
            "source_url",
            "source_sha256",
        ),
        "test",
    )
    row.update(document_version=None, order=1)
    assert provision_rows([row])[0][3] is None
