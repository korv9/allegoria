"""Run the bounded generation-one pilot, or validate source/prompts with --check (no API calls)."""

import argparse

from simulacria.anthropic_io import EXTRACTOR, TRANSFORMER
from simulacria.generation_one import prepare, run
from simulacria.selection.pools import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sources, tasks = prepare(PROJECT_ROOT)
    print(f"Sources: {len(sources)}, transformations: {len(tasks)}, depth: 1")
    print(f"Transformer: {TRANSFORMER}; reader: {EXTRACTOR}")
    if not args.check:
        print(run(PROJECT_ROOT))


if __name__ == "__main__":
    main()
