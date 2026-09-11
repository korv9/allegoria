"""Literal evidence about known source slots, never semantic absence or direction."""

import re


def quote_evidence(text: str, quote: str) -> dict:
    if not text.strip() or not quote.strip():
        raise ValueError("text and quote must be nonempty")
    # Only whitespace may vary. Preserve actual target offsets and quotation.
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    matches = list(re.finditer(pattern, text))
    return {
        "literal_status": "found" if matches else "not_found_requires_review",
        "occurrences": len(matches),
        "evidence": [{"quote": m[0], "start": m.start(), "end": m.end()} for m in matches],
        "semantic_status": "unreviewed",
    }


def audit_slots(source: dict, generation: str) -> list[dict]:
    """A surviving phrase may move or be negated; it does not prove slot retention."""
    return [
        {"passage_id": source["passage_id"], **slot, **quote_evidence(generation, slot["quote"])}
        for slot in source["slots"]
    ]
