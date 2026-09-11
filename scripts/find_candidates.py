"""Shortlist provisions with duty / exception / qualifier structure.

Reads `data/local/provisions.jsonl` and surfaces the provisions worth reading by
hand when building the twinned corpus: those carrying all three moving parts
from DIRECTION.md -- a duty, a carve-out from it, and a condition on one of them.

Matching is heuristic keyword matching on Swedish deontic markers. This is a
shortlist for human selection, not a measurement: it is tuned for recall, so
expect false positives and read the text before picking. Which part a qualifier
attaches to -- the thing that decides the sign -- is deliberately NOT inferred
here. That is annotated by hand during corpus construction.

    python scripts/find_candidates.py                 # top 40, ranked
    python scripts/find_candidates.py --limit 100
    python scripts/find_candidates.py --max-chars 900 # corpus-sized passages
    python scripts/find_candidates.py --jsonl data/local/candidates.jsonl
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROVISIONS_PATH = PROJECT_ROOT / "data" / "local" / "provisions.jsonl"

# The worked example in DIRECTION.md. If it stops making the shortlist, the
# markers below have drifted away from what the metric is about.
REFERENCE_PROVISION = "sfs-2026-1281:K10P10"

Marker = tuple[str, re.Pattern[str], int]


def _markers(entries: list[tuple[str, str, int]]) -> list[Marker]:
    return [
        (label, re.compile(pattern, re.IGNORECASE), weight) for label, pattern, weight in entries
    ]


# 1. Duty -- what shall or shall not happen. Includes enabling modality (`får`),
#    since a permission is equally a thing an exception can hang off.
DUTY_MARKERS = _markers(
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
EXCEPTION_MARKERS = _markers(
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
QUALIFIER_MARKERS = _markers(
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

# Determinacy ladder (DIRECTION.md): a checkable qualifier is a better corpus
# passage than an untestable one, because its death is observable.
#
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

# Passages get hand-twinned into a fictional counterpart with identical
# structure. Very short ones carry no structure; very long ones are unworkable.
IDEAL_MIN_CHARS = 150
IDEAL_MAX_CHARS = 900


def score_provision(text: str) -> dict[str, object] | None:
    """Return marker hits and a rank score, or None if a part is missing."""
    duty = _hits(text, DUTY_MARKERS)
    exception = _hits(text, EXCEPTION_MARKERS)
    qualifier = _hits(text, QUALIFIER_MARKERS)
    if not (duty and exception and qualifier):
        return None

    specific = sorted({match.group(0).lower() for match in SPECIFIC_QUALIFIER.finditer(text)})
    vague = sorted({match.group(0).lower() for match in VAGUE_QUALIFIER.finditer(text)})

    # Score the clearest marker in each part rather than the sum of all of them.
    # A sprawling provision with eight markers is a worse corpus passage than a
    # clean three-part one, and summing would rank it above.
    score = _strength(duty) + _strength(exception) + _strength(qualifier)
    score += 4 * bool(specific) + bool(vague)
    if IDEAL_MIN_CHARS <= len(text) <= IDEAL_MAX_CHARS:
        score += 4

    return {
        "duty_markers": [label for label, _ in duty],
        "exception_markers": [label for label, _ in exception],
        "qualifier_markers": [label for label, _ in qualifier],
        "specific_qualifiers": specific,
        "vague_qualifiers": vague,
        "determinacy": "specific" if specific else ("vague" if vague else "unmarked"),
        "score": score,
    }


def _hits(text: str, markers: list[Marker]) -> list[tuple[str, int]]:
    return [(label, weight) for label, pattern, weight in markers if pattern.search(text)]


def _strength(hits: list[tuple[str, int]]) -> int:
    """Best marker in the category, plus a capped bonus for corroborating ones."""
    return max(weight for _, weight in hits) + min(2, len(hits) - 1)


def load_provisions(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise SystemExit(f"{path} not found. Run scripts/build_silver.py first.")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def shortlist(
    provisions: list[dict[str, object]],
    min_chars: int = 0,
    max_chars: int = 0,
) -> list[dict[str, object]]:
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


def _ladder_detail(candidate: dict[str, object]) -> str:
    found = candidate["specific_qualifiers"] or candidate["vague_qualifiers"]
    return f"  ({', '.join(found)})" if found else ""


def render(candidate: dict[str, object], max_text: int) -> str:
    text = str(candidate["text"])
    if max_text and len(text) > max_text:
        text = text[:max_text].rstrip() + " […]"

    location = " / ".join(
        part for part in (str(candidate["chapter"]), str(candidate["heading"])) if part
    )
    lines = [
        f"[{candidate['score']:>3}] {candidate['provision_id']}  {candidate['label']}",
        f"      {candidate['document_title']}",
    ]
    if location:
        lines.append(f"      {location}")
    lines += [
        f"      duty:       {', '.join(candidate['duty_markers'])}",
        f"      exception:  {', '.join(candidate['exception_markers'])}",
        f"      qualifier:  {', '.join(candidate['qualifier_markers'])}",
        f"      determinacy: {candidate['determinacy']}{_ladder_detail(candidate)}",
        f"      {candidate['char_count']} chars · {candidate['source_url']}",
        "",
    ]
    lines += textwrap.indent(textwrap.fill(text, width=92), "      ").splitlines()
    return "\n".join(lines)


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provisions", type=Path, default=PROVISIONS_PATH)
    parser.add_argument("--limit", type=int, default=40, help="0 prints the whole shortlist")
    parser.add_argument("--min-chars", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=0, help="0 disables the length filter")
    parser.add_argument("--max-text", type=int, default=1200, help="truncate printed text")
    parser.add_argument("--jsonl", type=Path, help="also write the full shortlist here")
    args = parser.parse_args()

    provisions = load_provisions(args.provisions)
    candidates = shortlist(provisions, args.min_chars, args.max_chars)

    if args.jsonl:
        args.jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.jsonl.open("w", encoding="utf-8", newline="\n") as handle:
            for candidate in candidates:
                handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")

    shown = candidates if args.limit == 0 else candidates[: args.limit]
    for candidate in shown:
        print(render(candidate, args.max_text))
        print("-" * 92)

    specific = sum(1 for candidate in candidates if candidate["determinacy"] == "specific")
    documents = len({candidate["document_id"] for candidate in candidates})
    print(
        f"\n{len(candidates)} candidates from {documents} documents "
        f"({len(provisions)} provisions scanned, {specific} with a checkable qualifier). "
        f"Showing {len(shown)}."
    )
    if args.jsonl:
        print(f"Full shortlist written to {args.jsonl}")

    rank = next(
        (i for i, c in enumerate(candidates, 1) if c["provision_id"] == REFERENCE_PROVISION),
        None,
    )
    print(
        f"DIRECTION.md worked example {REFERENCE_PROVISION}: "
        + (f"rank {rank}." if rank else "NOT in the shortlist -- markers have drifted.")
    )


if __name__ == "__main__":
    main()
