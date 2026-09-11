"""Build the local Silver layer: bronze SFS JSON -> provisions.jsonl.

Pure Python. No Spark, no lakehouse-engine, no cluster. This is the local
equivalent of `products/allegoria/silver/silver_sfs.py`, and against the frozen
v1 snapshot it must produce the same rows: 1,952 provisions from 50 documents.

    python scripts/build_silver.py              # v1, the frozen 50-law corpus
    python scripts/build_silver.py --pool v2    # the larger selection pool

A thin wrapper. The build lives in `simulacria.selection.pools`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from simulacria.selection.pools import POOLS, build


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", choices=sorted(POOLS), default="v1")
    parser.add_argument("--bronze-dir", type=Path, help="override the pool's bronze directory")
    parser.add_argument("--output", type=Path, help="override the pool's output path")
    args = parser.parse_args()

    pool = POOLS[args.pool]
    bronze_dir = args.bronze_dir or pool.bronze_dir
    output_path = args.output or pool.output_path
    provisions, unparsable = build(bronze_dir, output_path, pool)

    kinds: dict[str, int] = {}
    for provision in provisions:
        kind = str(provision["kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    kind_summary = ", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items()))
    documents = len({str(provision["document_id"]) for provision in provisions})

    skipped = f", {len(unparsable)} unparsable skipped" if unparsable else ""
    print(
        f"SILVER {pool.name} | {documents} documents{skipped} -> {len(provisions)} provisions "
        f"({kind_summary}) | output: {output_path}"
    )


if __name__ == "__main__":
    main()
