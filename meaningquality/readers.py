"""Readers turn text into slot observations. The engine consumes observations,
not text, so any reader plugs in behind one shape:

    read(text, slots) -> {slot_id: {"status": "present"|"absent"|"uncertain",
                                     "quote": str | None, "determinacy"?: str}}

Reader quality is a separate question from the metric, measured by agreement with
a human (see PROTOCOL.md). These two are the deterministic, model-free examples;
an LLM reader is the same shape with a model behind it.
"""

from __future__ import annotations

from typing import Protocol


class Reader(Protocol):
    def read(self, text: str, slots: list[dict]) -> dict: ...


def annotation_reader(readings: dict) -> dict:
    """Pass-through for pre-annotated readings -- the human ground truth. The
    caller already holds `{slot_id: observation}`; this simply names it a reader."""
    return dict(readings)


class VerbatimReader:
    """A slot is present iff its source anchor phrase (its `quote`) still occurs
    verbatim in the target text. Answers 'did this clause survive?' -- exact,
    auditable, LLM-free -- but blind to paraphrase and to the determinacy rung, so
    it resolves removals, not softenings. Good for versioned or near-verbatim
    derivatives; the wrong tool for loose rhetoric."""

    def read(self, text: str, slots: list[dict]) -> dict:
        out = {}
        for slot in slots:
            quote = slot.get("quote")
            present = bool(quote) and quote in text
            out[slot["slot_id"]] = {
                "status": "present" if present else "absent",
                "quote": quote if present else None,
            }
        return out
