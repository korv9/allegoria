"""SELECTION. The determinacy ladder, applied to pick specimens.

Not measurement. `DIRECTION.md` defines the ladder -- `specific`, `vague`,
`absent` -- as a property of an annotated slot. What this module does is
approximate it from raw text so that provisions whose qualifier can be watched
falling down the ladder float to the top of a shortlist. The real grading of a
slot happens by hand at corpus construction.

Two figures are produced and they are not interchangeable:

`provision_determinacy`
    Graded over the whole text. Cheap, and what the ranking score uses.

`qualifier_determinacy`
    Graded over the qualifier clause only. This is the one that matches the
    ladder's actual subject, and the one to select specimens on. Measuring over
    the whole provision counted deadlines sitting in the duty or the exception:
    sfs-2023-560:P15 read `specific` on "tre månader" and "sex månader" while
    its qualifier, "Om det finns särskilda skäl", is not checkable at all.

Known limitation, documented rather than hidden: the qualifier span runs from a
marker to the end of its clause, and clause end is approximated by punctuation.
Swedish often omits the comma before a main clause, so a span can overrun into a
consequent -- in `sfs-2022-700:K3P9` it swallows a ceiling. A regex cannot find
the end of a Swedish conditional clause reliably.
"""

from __future__ import annotations

import re

from simulacria.selection.markers import QUALIFIER_MARKERS

# The number words are an enumerated closed class, not a wildcard: "fyrtio år"
# has to be as checkable as "två år", and the list originally stopped at
# "trettio", which read sfs-2026-1283:K5P1 as `unmarked` despite its forty-year
# review period. Compounds are spelled out because Swedish writes them solid
# ("tjugofyra timmar"), and longer alternatives are listed first so alternation
# prefers them.
_NUMBER_WORDS = (
    r"\d+"
    r"|tjugofyra|tjugofem|tjugosex|tjugosju|tjugoåtta|tjugonio|tjugoen|tjugoett"
    r"|tjugotvå|tjugotre|trettiosex|fyrtiofem|fyrtioåtta"
    r"|tretton|fjorton|femton|sexton|sjutton|arton|nitton"
    r"|tjugo|trettio|fyrtio|femtio|sextio|sjuttio|åttio|nittio|hundra"
    r"|elva|tolv|tio|en|ett|två|tre|fyra|fem|sex|sju|åtta|nio"
)
SPECIFIC_QUALIFIER = re.compile(
    rf"\b(?:{_NUMBER_WORDS})"
    r"\s+(?:kalender|arbets|vecko)?(?:dygn|dagar?|veckor?|månader?|år|timmar?)\b"
    r"|\bsenast\s+den\b|\bsenare\s+än\b|\bvid\s+utgången\s+av\b",
    re.IGNORECASE,
)
VAGUE_QUALIFIER = re.compile(
    r"\bskälig\w*\b|\bskyndsam\w*\b|\butan\s+dröjsmål\b|\bsnarast\b|\bom\s+möjligt\b"
    r"|\blämplig\w*\b|\bbehövlig\w*\b|\bi\s+god\s+tid\b",
    re.IGNORECASE,
)

QUALIFIER_CLAUSE_END = re.compile(r"[.,;:]")


def qualifier_spans(text: str) -> list[str]:
    """The clause each qualifier marker opens, for per-slot determinacy."""
    spans: list[str] = []
    for _label, pattern, _weight in QUALIFIER_MARKERS:
        for match in pattern.finditer(text):
            end = QUALIFIER_CLAUSE_END.search(text, match.end())
            spans.append(text[match.start() : end.start() if end else len(text)])
    return spans


def qualifier_spans_with_offsets(text: str) -> list[tuple[str, str, int, int]]:
    """As `qualifier_spans`, but keeping the marker label and character offsets.

    Returns (label, span, start, end). The notebook uses this to show which span
    was graded rather than only the verdict.
    """
    spans: list[tuple[str, str, int, int]] = []
    for label, pattern, _weight in QUALIFIER_MARKERS:
        for match in pattern.finditer(text):
            end_match = QUALIFIER_CLAUSE_END.search(text, match.end())
            end = end_match.start() if end_match else len(text)
            spans.append((label, text[match.start() : end], match.start(), end))
    return spans


def classify(text: str) -> str:
    """Grade a span on the ladder: `specific`, `vague` or `unmarked`."""
    if SPECIFIC_QUALIFIER.search(text):
        return "specific"
    return "vague" if VAGUE_QUALIFIER.search(text) else "unmarked"


def provision_determinacy(text: str) -> tuple[str, list[str], list[str]]:
    """Grade the whole provision. Returns (state, specific hits, vague hits)."""
    specific = sorted({match.group(0).lower() for match in SPECIFIC_QUALIFIER.finditer(text)})
    vague = sorted({match.group(0).lower() for match in VAGUE_QUALIFIER.finditer(text)})
    state = "specific" if specific else ("vague" if vague else "unmarked")
    return state, specific, vague


def qualifier_determinacy(text: str) -> tuple[str, list[str], list[str]]:
    """Grade the qualifiers themselves. Returns (state, specific hits, vague hits).

    A provision is `specific` only if some qualifier clause carries a checkable
    bound of its own. That is what decides whether a passage can show the
    two-step fall the founding observation turned on -- a vague qualifier has
    only one rung left to drop.
    """
    specific: set[str] = set()
    vague: set[str] = set()
    for span in qualifier_spans(text):
        specific |= {match.group(0).lower() for match in SPECIFIC_QUALIFIER.finditer(span)}
        vague |= {match.group(0).lower() for match in VAGUE_QUALIFIER.finditer(span)}

    state = "specific" if specific else ("vague" if vague else "unmarked")
    return state, sorted(specific), sorted(vague)
