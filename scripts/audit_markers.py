"""Audit the candidate markers: determinacy deltas and wildcard-shaped patterns.

Measurement only. This script never changes a pattern -- it reports what the
patterns currently do, so a change can be argued for separately.

    python scripts/audit_markers.py determinacy-delta --pool v1
    python scripts/audit_markers.py wildcard-inventory --pool v1 --sample 20

`determinacy-delta` compares the historical SPECIFIC_QUALIFIER (number words
stopping at "trettio") against the one in force, and reports which provisions
change rung on the DIRECTION.md ladder.

`wildcard-inventory` lists every marker whose pattern contains `\\w+` or a
bounded repetition, samples its hits with surrounding context, and reports
whether the matched span crosses a clause boundary.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_silver import POOLS
from scripts.find_candidates import (
    DUTY_MARKERS,
    EXCEPTION_MARKERS,
    QUALIFIER_MARKERS,
    SPECIFIC_QUALIFIER,
    VAGUE_QUALIFIER,
    load_provisions,
)

# The pattern as it stood before 2026-09-11. Kept verbatim as a baseline so the
# delta is measurable; it is never used for scoring.
LEGACY_SPECIFIC_QUALIFIER = re.compile(
    r"\b(?:\d+|en|ett|två|tre|fyra|fem|sex|sju|åtta|nio|tio|tolv|fjorton|femton|tjugo|trettio)"
    r"\s+(?:kalender|arbets|vecko)?(?:dygn|dagar?|veckor?|månader?|år|timmar?)\b"
    r"|\bsenast\s+den\b|\bsenare\s+än\b|\bvid\s+utgången\s+av\b",
    re.IGNORECASE,
)

MARKER_SETS = (
    ("duty", DUTY_MARKERS),
    ("exception", EXCEPTION_MARKERS),
    ("qualifier", QUALIFIER_MARKERS),
)

# Tokens that end the clause an `om ... inte` gap started in. A span containing
# one of these has left the conditional it claims to mark.
CLAUSE_BOUNDARY = re.compile(
    r"[,;:]|\b(?:att|men|som|och|eller|vilket|där|när|då)\b", re.IGNORECASE
)

# `\w+` and `\w*` are unbounded wildcards; `{n,m}` is the bounded repetition that
# stands in for "same clause". All three are the shape Part C is inventorying.
WILDCARD_SHAPE = re.compile(r"\\w[+*]|\{\d+,\d*\}")


# A `dock` that introduces an upper bound on a granted power, rather than a
# carve-out from an obligation. The bound words are a closed class; the window
# is small because the bound follows its `dock` closely in practice.
BOUND_WORDS = re.compile(
    r"\b(?:högst|längst|minst|tidigast|senast|mest|inte\s+överstiga|"
    r"inte\s+(?:\w+\s+){0,2}?längre\s+än)\b",
    re.IGNORECASE,
)
DOCK = re.compile(r"\bdock\b", re.IGNORECASE)
CEILING_WINDOW = 60


def ceiling_hits(text: str) -> list[tuple[str, bool]]:
    """Every `dock` with the span that follows it, and whether it carries a bound."""
    hits: list[tuple[str, bool]] = []
    for match in DOCK.finditer(text):
        window = text[match.start() : match.end() + CEILING_WINDOW]
        hits.append((window.replace("\n", " "), bool(BOUND_WORDS.search(window))))
    return hits


def determinacy(text: str, specific: re.Pattern[str]) -> str:
    if specific.search(text):
        return "specific"
    return "vague" if VAGUE_QUALIFIER.search(text) else "unmarked"


def determinacy_delta(provisions: list[dict[str, object]]) -> dict[str, object]:
    changes: list[dict[str, str]] = []
    for provision in provisions:
        text = str(provision["text"])
        before = determinacy(text, LEGACY_SPECIFIC_QUALIFIER)
        after = determinacy(text, SPECIFIC_QUALIFIER)
        if before != after:
            gained = sorted(
                {match.group(0).lower() for match in SPECIFIC_QUALIFIER.finditer(text)}
                - {match.group(0).lower() for match in LEGACY_SPECIFIC_QUALIFIER.finditer(text)}
            )
            changes.append(
                {
                    "provision_id": str(provision["provision_id"]),
                    "before": before,
                    "after": after,
                    "newly_matched": ", ".join(gained),
                }
            )
    return {"scanned": len(provisions), "changed": len(changes), "changes": changes}


def wildcard_inventory(
    provisions: list[dict[str, object]], sample_size: int, seed: int
) -> list[dict[str, object]]:
    rng = random.Random(seed)
    report: list[dict[str, object]] = []

    for category, markers in MARKER_SETS:
        for label, pattern, _weight in markers:
            if not WILDCARD_SHAPE.search(pattern.pattern):
                continue

            hits: list[tuple[str, str, str]] = []
            for provision in provisions:
                text = str(provision["text"])
                for match in pattern.finditer(text):
                    span = match.group(0)
                    context = text[max(0, match.start() - 60) : match.end() + 60]
                    hits.append((str(provision["provision_id"]), span, context))

            crossing = [hit for hit in hits if CLAUSE_BOUNDARY.search(hit[1])]
            sample = rng.sample(hits, min(sample_size, len(hits))) if hits else []
            report.append(
                {
                    "category": category,
                    "marker": label,
                    "pattern": pattern.pattern,
                    "hits": len(hits),
                    "clause_crossing_hits": len(crossing),
                    "crossing_rate": round(len(crossing) / len(hits), 4) if hits else 0.0,
                    "sample": [
                        {"provision_id": pid, "span": span, "context": ctx.replace("\n", " ")}
                        for pid, span, ctx in sample
                    ],
                    "crossing_examples": [
                        {"provision_id": pid, "span": span} for pid, span, _ctx in crossing[:6]
                    ],
                }
            )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("determinacy-delta", "wildcard-inventory", "ceiling-scan"))
    parser.add_argument("--pool", choices=sorted(POOLS), default="v1")
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--json", type=Path, help="write the full report here")
    args = parser.parse_args()

    provisions = load_provisions(POOLS[args.pool].output_path)

    if args.mode == "determinacy-delta":
        result = determinacy_delta(provisions)
        print(
            f"DETERMINACY {args.pool} | scanned {result['scanned']} provisions | "
            f"{result['changed']} changed rung"
        )
        for change in result["changes"][:15]:
            print(
                f"  {change['provision_id']:<34} {change['before']:>8} -> "
                f"{change['after']:<8} via {change['newly_matched']}"
            )
        if result["changed"] > 15:
            print(f"  ... {result['changed'] - 15} more")
        payload: object = result
    elif args.mode == "ceiling-scan":
        from scripts.find_candidates import shortlist

        candidates = shortlist(provisions)
        flagged = []
        for candidate in candidates:
            hits = ceiling_hits(str(candidate["text"]))
            bounded = [window for window, has_bound in hits if has_bound]
            if bounded:
                flagged.append(
                    {
                        "provision_id": str(candidate["provision_id"]),
                        "char_count": candidate["char_count"],
                        "windows": bounded,
                    }
                )
        with_dock = sum(1 for c in candidates if DOCK.search(str(c["text"])))
        print(
            f"CEILING SCAN {args.pool} | {len(candidates)} candidates | "
            f"{with_dock} carry `dock` | {len(flagged)} carry `dock` + a bound "
            f"({len(flagged) / with_dock:.1%} of dock candidates)"
        )
        for entry in flagged[:10]:
            print(f"  {entry['provision_id']:<34} {entry['windows'][0][:72]!r}")
        payload = {"candidates": len(candidates), "with_dock": with_dock, "flagged": flagged}
    else:
        payload = wildcard_inventory(provisions, args.sample, args.seed)
        print(f"WILDCARD MARKERS {args.pool} | seed {args.seed}")
        for entry in payload:
            print(
                f"  {entry['category']:<10} {entry['marker']:<26} "
                f"hits {entry['hits']:>5}  clause-crossing {entry['clause_crossing_hits']:>4} "
                f"({entry['crossing_rate']:.1%})"
            )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  full report: {args.json}")


if __name__ == "__main__":
    main()
