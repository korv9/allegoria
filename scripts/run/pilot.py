"""Run the bounded generation-one pilot for one experiment config.

    python scripts/run/pilot.py --check          # plan only, no API calls
    python scripts/run/pilot.py                  # configs/pilot-sv.yaml
    python scripts/run/pilot.py --config configs/rfc-en.yaml --limit-usd 0.2
    python scripts/run/pilot.py --transformer opus-5 --extractor haiku-4-5

`--check` resolves every passage through its domain adapter and builds every
request, so a broken corpus, a moved source file or a missing prompt fails here
rather than after the first paid call. Model names come from configs/models.yaml.
"""

import argparse
from pathlib import Path

from simulacria.generation.models import registry, resolve, unverified
from simulacria.generation.pilot import prepare, run
from simulacria.generation.plan import PILOT_CONFIG, load_config

ROOT = Path(__file__).resolve().parents[2]


def describe(models: dict) -> None:
    for role, spec in models.items():
        seen = f"verified {spec.verified}" if spec.verified else "NOT VERIFIED"
        print(
            f"{role:>12}: {spec.name} ({spec.provider}/{spec.model}) "
            f"${spec.input_usd_per_million}/${spec.output_usd_per_million} per Mtok, {seen}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=PILOT_CONFIG, help="experiment config under configs/")
    parser.add_argument("--transformer", help="override the config's transformer model name")
    parser.add_argument("--extractor", help="override the config's extractor model name")
    parser.add_argument("--limit-usd", type=float, default=0.50, help="hard local spend ceiling")
    parser.add_argument("--check", action="store_true", help="plan and validate, spend nothing")
    parser.add_argument("--list-models", action="store_true", help="print the model registry")
    parser.add_argument(
        "--allow-unverified-model",
        action="store_true",
        help="spend on a model nobody has called through this code yet",
    )
    args = parser.parse_args()

    if args.list_models:
        for name, spec in registry().items():
            seen = f"verified {spec.verified}" if spec.verified else "unverified"
            print(f"{name:<14} {spec.provider:<10} {spec.model:<32} {seen}")
        return

    config = load_config(ROOT, args.config)
    overrides = {
        k: v for k, v in (("transformer", args.transformer), ("extractor", args.extractor)) if v
    }
    if overrides:
        config["models"] = {**(config.get("models") or {}), **overrides}
    models = resolve(config)
    sources, tasks = prepare(ROOT, config)

    print(f"Experiment: {config['experiment']} ({config['config_path']})")
    print(
        f"Domains: {', '.join(sorted({s['domain'] for s in sources}))}; "
        f"language: {config.get('language', 'unspecified')}"
    )
    print(f"Sources: {len(sources)}, transformations: {len(tasks)}, depth: 1")
    print(f"Readings: {len(tasks) + len(sources)} (every text is read once)")
    describe(models)

    risky = unverified(models)
    if risky:
        names = ", ".join(spec.name for spec in risky)
        print(f"\nWARNING: no call has ever been made through this code with: {names}.")
        print(
            "Run scripts/investigations/check_provider.py first, or pass --allow-unverified-model."
        )
        if not args.check and not args.allow_unverified_model:
            raise SystemExit(1)
    if not args.check:
        print(run(ROOT, args.limit_usd, config))


if __name__ == "__main__":
    main()
