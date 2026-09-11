"""SELECTION. Swedish deontic marker sets and the scoring built on them.

Not measurement. These regexes decide which provisions are worth a human's
attention; they say nothing about what a provision means. They are tuned for
recall, so they carry known false positives -- see `review/` for the audited
ones -- and a marker firing is an invitation to read the text, never a finding.

Which part a qualifier attaches to is deliberately absent from this module.
That decides the sign of a removal, and `DIRECTION.md` assigns it to hand
annotation.
"""

from __future__ import annotations

import re

Marker = tuple[str, re.Pattern[str], int]


def compile_markers(entries: list[tuple[str, str, int]]) -> list[Marker]:
    """Compile (label, pattern, weight) triples into case-insensitive markers."""
    return [
        (label, re.compile(pattern, re.IGNORECASE), weight) for label, pattern, weight in entries
    ]


# 1. Duty -- what shall or shall not happen. Includes enabling modality (`får`),
#    since a permission is equally a thing an exception can hang off.
DUTY_MARKERS = compile_markers(
    [
        ("ska", r"\bska(?:ll)?\b", 2),
        ("får inte", r"\bfår\s+(?:\w+\s+){0,3}?inte\b", 2),
        ("måste", r"\bmåste\b", 2),
        ("är skyldig", r"\b(?:är|blir)\s+skyldiga?\b|\båligger\b", 2),
        ("förbjuden", r"\bförbjud(?:en|et|na)\b|\bförbud\b", 2),
        ("bör", r"\bbör\b", 1),
        ("får", r"\bfår\b", 1),
        ("har rätt att", r"\b(?:har|äger)\s+rätt\s+(?:att|till)\b", 1),
    ]
)

# 2. Exception -- a carve-out from the duty.
EXCEPTION_MARKERS = compile_markers(
    [
        ("dock", r"\bdock\b", 3),
        ("om inte", r"\bom\s+(?:\w+\s+){0,3}?inte\b", 3),
        ("såvida inte", r"\bsåvida\s+inte\b|\bmed\s+mindre\s+än\b", 3),
        ("undantag", r"\bundantag\w*\b", 3),
        ("trots", r"\btrots\s+(?:vad|att|bestämmelserna|första|andra|detta)\b", 3),
        ("utan hinder av", r"\butan\s+hinder\s+av\b", 3),
        ("utom", r"\butom\b|\bmed\s+undantag\s+för\b", 3),
        ("annat än", r"\b(?:om\s+)?(?:inte\s+)?annat\s+(?:än|följer|föreskrivs|anges)\b", 2),
        ("gäller inte", r"\bgäller\s+(?:dock\s+)?inte\b|\btillämpas\s+(?:dock\s+)?inte\b", 2),
        ("ska inte", r"\bska(?:ll)?\s+(?:dock\s+)?inte\b", 2),
        ("behöver inte", r"\bbehöver\s+inte\b|\bkrävs\s+inte\b|\bfordras\s+inte\b", 2),
        ("i stället", r"\bi\s+stället\b", 1),
    ]
)

# 3. Qualifier -- a condition on the duty or on the exception. Bare `om` / `när`
#    are weak but kept: recall over precision, and the ranking sorts it out.
QUALIFIER_MARKERS = compile_markers(
    [
        ("under förutsättning att", r"\b(?:under\s+förutsättning|förutsatt)\s+att\b", 4),
        ("endast om", r"\b(?:endast|bara)\s+(?:om|när|i\s+de\s+fall)\b", 4),
        ("i den mån", r"\bi\s+den\s+mån\b|\bsåvitt\b|\bi\s+fråga\s+om\b", 2),
        # Same scope-limiting job as `i den mån`, different wording. Found via
        # sfs-2026-456:P2 ("i den utsträckning som denna lag avviker"), which the
        # markers were rejecting as a near-miss. Kept as its own label so the
        # marker_hits table can show how much each variant actually earns.
        (
            "i den utsträckning",
            r"\bi\s+den\s+utsträckning\b|\btill\s+den\s+del\b|\bi\s+den\s+omfattning\b",
            2,
        ),
        ("om", r"\bom\b", 1),
        ("när/vid", r"\bnär\b|\bvid\s+(?:sådan|denna|en|det)\b|\bi\s+de\s+fall\b", 1),
        ("efter det att", r"\befter\s+det\s+att\b|\binnan\b|\bsedan\b", 1),
        ("särskilda skäl", r"\b(?:särskilda|synnerliga|godtagbara)\s+skäl\b", 2),
    ]
)

MARKER_SETS: tuple[tuple[str, list[Marker]], ...] = (
    ("duty", DUTY_MARKERS),
    ("exception", EXCEPTION_MARKERS),
    ("qualifier", QUALIFIER_MARKERS),
)


def hits(text: str, markers: list[Marker]) -> list[tuple[str, int]]:
    """Which markers in a set fire on this text, as (label, weight) pairs.

    Presence only, one entry per marker however often it matches. Use
    `iter_matches` when the positions matter.
    """
    return [(label, weight) for label, pattern, weight in markers if pattern.search(text)]


def iter_matches(text: str, markers: list[Marker]):
    """Every marker occurrence with its span, for highlighting and offsets.

    Yields (label, match) in marker-list order. The caller gets real `re.Match`
    objects so `matched_span` stays a verbatim substring of the input --
    `PROTOCOL.md` requires that of anything claiming to quote its source.
    """
    for label, pattern, _weight in markers:
        for match in pattern.finditer(text):
            yield label, match


def strength(marker_hits: list[tuple[str, int]]) -> int:
    """Score one category: its heaviest marker, plus a capped corroboration bonus.

    Scoring the best marker rather than summing all of them keeps a sprawling
    provision with eight weak markers below a clean three-part one.
    """
    return max(weight for _, weight in marker_hits) + min(2, len(marker_hits) - 1)


def top_marker(text: str, markers: list[Marker]) -> str | None:
    """The marker that carried a category's score, or None if none fired.

    `strength` scores a category by its heaviest hit and `max` keeps the first
    maximal element, so this resolves ties the way the ranking does: by order in
    the marker list.
    """
    fired = hits(text, markers)
    return max(fired, key=lambda hit: hit[1])[0] if fired else None


# Tokens that end the clause an `om ... inte` gap started in. A span containing
# one of these has left the conditional it claims to mark. Used by the marker
# audit and by gold-set sampling, not by scoring.
CLAUSE_BOUNDARY = re.compile(
    r"[,;:]|\b(?:att|men|som|och|eller|vilket|där|när|då)\b", re.IGNORECASE
)

# A `dock` that introduces an upper bound on a granted power, rather than a
# carve-out from an obligation. The bound words are a closed class; the window
# is small because the bound follows its `dock` closely in practice.
#
# This FLAGS the pattern, it does not classify it. Whether a `dock` clause is a
# ceiling or an exception decides the sign of its removal, so it is resolved by
# hand -- see `review/2026-09-11/DIRECTION-ceiling-proposal.md`. Measured precision of the
# flag on v1 is roughly 53%: 9 true ceilings out of 17 flags.
BOUND_WORDS = re.compile(
    r"\b(?:högst|längst|minst|tidigast|senast|mest|inte\s+överstiga|"
    r"inte\s+(?:\w+\s+){0,2}?längre\s+än)\b",
    re.IGNORECASE,
)
DOCK = re.compile(r"\bdock\b", re.IGNORECASE)
CEILING_WINDOW = 60


def ceiling_hits(text: str) -> list[tuple[str, bool]]:
    """Every `dock` with the span that follows it, and whether it carries a bound."""
    hits_found: list[tuple[str, bool]] = []
    for match in DOCK.finditer(text):
        window = text[match.start() : match.end() + CEILING_WINDOW]
        hits_found.append((window.replace("\n", " "), bool(BOUND_WORDS.search(window))))
    return hits_found
