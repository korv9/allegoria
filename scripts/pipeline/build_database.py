"""Build the local DuckDB analysis database from saved evidence. No API calls."""

import argparse
from pathlib import Path

from simulacria.pipeline.gold import build_database

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=root / "data/local/allegoria.duckdb")
    parser.add_argument("--pool", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    print(build_database(root, args.database, args.pool))
