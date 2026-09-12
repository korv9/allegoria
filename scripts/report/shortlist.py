"""Shortlist provisions with duty / exception / qualifier structure.

Reads a pool's `provisions.jsonl` and surfaces the provisions worth reading by
hand when building the twinned corpus: those carrying all three moving parts
from DIRECTION.md -- a duty, a carve-out from it, and a condition on one of them.

Matching is heuristic keyword matching on Swedish deontic markers. This is a
shortlist for human selection, not a measurement: it is tuned for recall, so
expect false positives and read the text before picking. Which part a qualifier
attaches to -- the thing that decides the sign -- is deliberately NOT inferred
here. That is annotated by hand during corpus construction.

    python scripts/report/shortlist.py                 # top 40, ranked
    python scripts/report/shortlist.py --pool v2 --limit 100
    python scripts/report/shortlist.py --max-chars 900 # corpus-sized passages
    python scripts/report/shortlist.py --jsonl data/local/candidates.jsonl

A thin wrapper. The markers, the ladder and the scoring live in
`simulacria.selection`.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import textwrap
from pathlib import Path

from simulacria.pipeline.silver import POOLS, load_provisions
from simulacria.selection.shortlist import shortlist

# The worked example in DIRECTION.md. If it stops making the shortlist, the
# markers have drifted away from what the metric is about.
REFERENCE_PROVISION = "sfs-2026-1281:K10P10"


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
        f"      qualifier determinacy: {candidate['qualifier_determinacy']}",
        f"      {candidate['char_count']} chars · {candidate['source_url']}",
        "",
    ]
    lines += textwrap.indent(textwrap.fill(text, width=92), "      ").splitlines()
    return "\n".join(lines)


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", choices=sorted(POOLS), default="v1")
    parser.add_argument("--provisions", type=Path, help="override the pool's provisions.jsonl")
    parser.add_argument("--limit", type=int, default=40, help="0 prints the whole shortlist")
    parser.add_argument("--min-chars", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=0, help="0 disables the length filter")
    parser.add_argument("--max-text", type=int, default=1200, help="truncate printed text")
    parser.add_argument("--jsonl", type=Path, help="also write the full shortlist here")
    args = parser.parse_args()

    provisions_path = args.provisions or POOLS[args.pool].output_path
    provisions = load_provisions(provisions_path)
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
    qualifier_specific = sum(
        1 for candidate in candidates if candidate["qualifier_determinacy"] == "specific"
    )
    documents = len({candidate["document_id"] for candidate in candidates})
    print(
        f"\n{len(candidates)} candidates from {documents} documents "
        f"({len(provisions)} provisions scanned, {specific} specific at provision level, "
        f"{qualifier_specific} with a checkable qualifier). Showing {len(shown)}."
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
