"""Run or resume recorded generation 1-10 chains. This command makes paid API calls."""

import argparse
from pathlib import Path

from simulacria.recursive_run import create, execute

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--limit-usd", type=float, default=15)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stage", choices=("all", "generate", "read"), default="all")
    parser.add_argument(
        "--group",
        choices=("all", "statutory", "virtue", "categorical", "conditional"),
        default="all",
    )
    parser.add_argument(
        "--interval", type=float, default=6.2, help="minimum seconds between API starts"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = args.resume or create(root, args.limit_usd)
    print("ARTIFACTS", directory, flush=True)
    execute(root, directory, args.workers, args.stage, args.group, args.interval)
