"""Sample `om inte` hits for hand-labelling into a gold set.

Extraction only -- this script assigns no labels. It emits the sample with
context so a human (or, here, a careful read) can label each hit, and it is run
BEFORE any fix so the evaluation cannot be tuned to the fix.

    python scripts/sample_om_inte.py --out review/2026-09-11/evidence/om_inte_sample.json

Selection, in priority order:

1. Every v1 hit whose matched span crosses a clause boundary -- the known
   defective set.
2. Every hit in a provision ranked in the top 50 of either pool.
3. The remainder drawn at random from what is left, with a recorded seed.

A hit present in both pools is one entry: v2 is a superset of v1, and the same
sentence should not be labelled twice.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from simulacria.selection.markers import CLAUSE_BOUNDARY, EXCEPTION_MARKERS
from simulacria.selection.pools import POOLS, load_provisions
from simulacria.selection.tables import connect

CONTEXT_CHARS = 120
TARGET_SAMPLE = 80
DEFAULT_SEED = 20260911

OM_INTE = next(pattern for label, pattern, _w in EXCEPTION_MARKERS if label == "om inte")


def _ranks(pool: str) -> dict[str, int]:
    connection = connect(POOLS[pool].tables_dir)
    try:
        rows = connection.execute("select provision_id, rank from candidates").fetchall()
    finally:
        connection.close()
    return {str(pid): int(rank) for pid, rank in rows}


def collect_hits() -> list[dict[str, object]]:
    hits: dict[tuple[str, int, str], dict[str, object]] = {}

    for pool in ("v1", "v2"):
        ranks = _ranks(pool)
        for provision in load_provisions(POOLS[pool].output_path):
            text = str(provision["text"])
            provision_id = str(provision["provision_id"])
            for match in OM_INTE.finditer(text):
                span, offset = match.group(0), match.start()
                key = (provision_id, offset, span)
                if key in hits:
                    entry = hits[key]
                    if pool not in entry["pools"]:
                        entry["pools"].append(pool)
                        entry[f"rank_{pool}"] = ranks.get(provision_id)
                    continue
                hits[key] = {
                    "provision_id": provision_id,
                    "document_title": str(provision["document_title"]),
                    "span": span,
                    "char_offset": offset,
                    "context": text[
                        max(0, offset - CONTEXT_CHARS) : offset + len(span) + CONTEXT_CHARS
                    ].replace("\n", " "),
                    "crosses_clause_boundary": bool(CLAUSE_BOUNDARY.search(span)),
                    "pools": [pool],
                    "rank_v1": ranks.get(provision_id) if pool == "v1" else None,
                    "rank_v2": ranks.get(provision_id) if pool == "v2" else None,
                }
    return list(hits.values())


def select(
    hits: list[dict[str, object]], size: int, seed: int, max_per_provision: int = 1
) -> dict[str, object]:
    """Stratify the sample: defective hits, top-50 coverage, then random fill.

    The top-50 stratum is capped per provision. Taking literally every hit in a
    top-50 provision is dominated by a handful of enormous transitional blocks
    -- one carries 95 `om inte` hits on its own -- which would spend most of the
    gold set relabelling one law's boilerplate. One seeded-random hit per
    provision covers all 57 top-50 provisions instead, keeping the natural mix
    of span shapes rather than preferring the odd-looking ones.
    """
    rng = random.Random(seed)

    def top50(hit: dict[str, object]) -> bool:
        return any(isinstance(hit[key], int) and hit[key] <= 50 for key in ("rank_v1", "rank_v2"))

    defective = [h for h in hits if h["crosses_clause_boundary"] and "v1" in h["pools"]]
    defective_keys = {id(h) for h in defective}

    by_provision: dict[str, list[dict[str, object]]] = {}
    for hit in hits:
        if id(hit) not in defective_keys and top50(hit):
            by_provision.setdefault(str(hit["provision_id"]), []).append(hit)
    ranked = [
        rng.choice(sorted(group, key=lambda h: int(h["char_offset"])))
        for _provision_id, group in sorted(by_provision.items())
        for _ in range(min(max_per_provision, 1))
    ]

    mandatory = defective + ranked
    mandatory_keys = {id(h) for h in mandatory}

    remainder = [h for h in hits if id(h) not in mandatory_keys]
    filler = rng.sample(remainder, min(max(0, size - len(mandatory)), len(remainder)))

    for hit, reason in (
        *((h, "known-defective-v1") for h in defective),
        *((h, "top-50-ranked") for h in ranked),
        *((h, f"random-seed-{seed}") for h in filler),
    ):
        hit["selection_reason"] = reason

    selected = mandatory + filler
    selected.sort(key=lambda h: (h["selection_reason"], str(h["provision_id"])))
    return {
        "total_hits": len(hits),
        "seed": seed,
        "counts": {
            "known_defective_v1": len(defective),
            "top_50_ranked": len(ranked),
            "top_50_provisions_covered": len(by_provision),
            "random_filler": len(filler),
            "selected": len(selected),
        },
        "stratified": (
            "Deliberately enriched with hard cases: every known-defective v1 hit is "
            "included. Precision measured on this set is a lower bound on corpus-wide "
            "precision, not an estimate of it."
        ),
        "hits": selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=int, default=TARGET_SAMPLE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    result = select(collect_hits(), args.size, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = result["counts"]
    print(
        f"OM INTE SAMPLE | {result['total_hits']} distinct hits | "
        f"selected {counts['selected']} "
        f"(defective {counts['known_defective_v1']}, top50 {counts['top_50_ranked']}, "
        f"random {counts['random_filler']}, seed {args.seed}) | {args.out}"
    )


if __name__ == "__main__":
    main()
