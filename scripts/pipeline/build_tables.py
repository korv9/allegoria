"""Build local analysis tables; transformations live in simulacria.pipeline.tables."""

import argparse
from pathlib import Path

from simulacria.pipeline.silver import POOLS
from simulacria.pipeline.tables import build_tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", choices=sorted(POOLS), default="v1")
    parser.add_argument("--provisions", type=Path, help="override the pool's provisions.jsonl")
    parser.add_argument("--tables-dir", type=Path, help="override the pool's table directory")
    args = parser.parse_args()

    provisions_path = args.provisions or POOLS[args.pool].output_path
    tables_dir = args.tables_dir or POOLS[args.pool].tables_dir
    counts = build_tables(provisions_path, tables_dir)

    summary = ", ".join(f"{name} {count}" for name, count in counts.items())
    print(f"TABLES {args.pool} | {summary} | output: {tables_dir}")


if __name__ == "__main__":
    main()
