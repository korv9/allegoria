"""Export one recorded run to portable Parquet, JSON and blind review files."""

import argparse
from pathlib import Path

from simulacria.recursive_export import export_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=Path("data/local/allegoria.duckdb"))
    args = parser.parse_args()
    print(export_results(args.run, args.out, args.database))
