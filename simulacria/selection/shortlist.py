"""SELECTION. Candidate scoring and ranking.

Not measurement. This decides reading order for a human picking corpus
specimens. A high rank means "worth reading first", never "more degraded" or
"more normatively significant" -- nothing here computes direction, and the score
must never be fed into a metric.

The score is deliberately crude: the strongest marker in each of the three
categories, a capped bonus for corroborating markers, a bonus for a checkable
qualifier, a bonus for twinnable length, ties broken toward shorter text. There
is no theory behind the weights and there does not need to be; they order a
reading list.
"""

from __future__ import annotations

from simulacria.selection.determinacy import provision_determinacy, qualifier_determinacy
from simulacria.selection.markers import (
    DUTY_MARKERS,
    EXCEPTION_MARKERS,
    QUALIFIER_MARKERS,
    hits,
    strength,
)

# Passages get hand-twinned into a fictional counterpart with identical
# structure. Very short ones carry no structure; very long ones are unworkable.
IDEAL_MIN_CHARS = 150
IDEAL_MAX_CHARS = 900

SPECIFIC_BONUS = 4
VAGUE_BONUS = 1
LENGTH_BONUS = 4


def score_provision(text: str) -> dict[str, object] | None:
    """Marker hits, determinacy and a rank score -- or None if a part is missing.

    A provision is a candidate only when all three parts fire. That is the whole
    gate; everything else is ordering.
    """
    duty = hits(text, DUTY_MARKERS)
    exception = hits(text, EXCEPTION_MARKERS)
    qualifier = hits(text, QUALIFIER_MARKERS)
    if not (duty and exception and qualifier):
        return None

    state, specific, vague = provision_determinacy(text)

    # Score the clearest marker in each part rather than the sum of all of them.
    # A sprawling provision with eight markers is a worse corpus passage than a
    # clean three-part one, and summing would rank it above.
    score = strength(duty) + strength(exception) + strength(qualifier)
    score += SPECIFIC_BONUS * bool(specific) + VAGUE_BONUS * bool(vague)
    if IDEAL_MIN_CHARS <= len(text) <= IDEAL_MAX_CHARS:
        score += LENGTH_BONUS

    # Two figures, deliberately kept apart. `determinacy` grades the provision
    # and drives the score, so the ranking is stable. The ladder in DIRECTION.md
    # is about the qualifier, and that is the one to select specimens on.
    qualifier_state, qualifier_specific, qualifier_vague = qualifier_determinacy(text)

    return {
        "duty_markers": [label for label, _ in duty],
        "exception_markers": [label for label, _ in exception],
        "qualifier_markers": [label for label, _ in qualifier],
        "specific_qualifiers": specific,
        "vague_qualifiers": vague,
        "determinacy": state,
        "qualifier_determinacy": qualifier_state,
        "qualifier_specific": qualifier_specific,
        "qualifier_vague": qualifier_vague,
        "score": score,
    }


def score_breakdown(text: str) -> dict[str, object] | None:
    """The same score, itemised -- what each category and bonus contributed.

    For inspection only. `score_provision` is the authority; this re-derives the
    parts from the same functions so the two cannot disagree.
    """
    duty = hits(text, DUTY_MARKERS)
    exception = hits(text, EXCEPTION_MARKERS)
    qualifier = hits(text, QUALIFIER_MARKERS)
    if not (duty and exception and qualifier):
        return None

    state, specific, vague = provision_determinacy(text)
    length_fit = IDEAL_MIN_CHARS <= len(text) <= IDEAL_MAX_CHARS
    components = {
        "duty": strength(duty),
        "exception": strength(exception),
        "qualifier": strength(qualifier),
        "specific_bonus": SPECIFIC_BONUS * bool(specific),
        "vague_bonus": VAGUE_BONUS * bool(vague),
        "length_bonus": LENGTH_BONUS * length_fit,
    }
    return {
        "components": components,
        "total": sum(components.values()),
        "determinacy": state,
        "length_fit": length_fit,
        "char_count": len(text),
        "category_hits": {"duty": duty, "exception": exception, "qualifier": qualifier},
    }


def shortlist(
    provisions: list[dict[str, object]],
    min_chars: int = 0,
    max_chars: int = 0,
) -> list[dict[str, object]]:
    """Every provision carrying all three parts, best-first."""
    candidates: list[dict[str, object]] = []
    for provision in provisions:
        text = str(provision["text"])
        if len(text) < min_chars or (max_chars and len(text) > max_chars):
            continue
        match = score_provision(text)
        if match is None:
            continue
        candidates.append({**provision, **match, "char_count": len(text)})

    # Ties break toward the shorter passage: less prose around the same three
    # parts is easier to twin by hand.
    candidates.sort(
        key=lambda row: (-int(row["score"]), int(row["char_count"]), str(row["provision_id"]))
    )
    return candidates


def ranked(provisions: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """The shortlist keyed by provision_id, each row carrying its 1-based rank."""
    return {
        str(candidate["provision_id"]): {"rank": rank, **candidate}
        for rank, candidate in enumerate(shortlist(provisions), start=1)
    }
