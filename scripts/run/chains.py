"""Run or resume recorded recursive chains. This command makes paid API calls.

    python scripts/run/chains.py --check                       # cost and size, no calls
    python scripts/run/chains.py --group statutory --limit-usd 6
    python scripts/run/chains.py --extractor opus-5 --check    # price a better reader
    python scripts/run/chains.py --config configs/rfc-en.yaml --limit-usd 5
    python scripts/run/chains.py --resume data/local/runs/recursive-<id>

A resumed run keeps the design frozen at creation: `--config` and the model
overrides are ignored with `--resume`, because the design on disk is what that
run means.
"""

import argparse
from pathlib import Path

from simulacria.generation.chains import execute
from simulacria.generation.design import create
from simulacria.generation.models import registry, resolve, suggested_interval, unverified
from simulacria.generation.plan import DEFAULT_CONFIG, load_config, plan

ROOT = Path(__file__).resolve().parents[2]

# Measured means from the model probe: ~900 in / ~350 out per transformation,
# ~1,200 in / ~450 out per reading. An estimate from real usage, never a quote.
TRANSFORM_TOKENS = (900, 350)
READ_TOKENS = (1200, 450)


def estimate(config: dict) -> dict:
    """Rough cost from measured per-call usage, printed before anything is spent."""
    sources, chains = plan(ROOT, config)
    models = resolve(config)
    transformations = len(chains) * config["generations"]
    readings = transformations + len(sources)
    cost = transformations * models["transformer"].cost(*TRANSFORM_TOKENS)
    cost += readings * models["extractor"].cost(*READ_TOKENS)

    print(f"Experiment: {config['experiment']} ({config['config_path']})")
    print(f"Passages: {len(sources)}; chains: {len(chains)}; generations: {config['generations']}")
    print(f"Planned: {transformations} transformations, {readings} readings")
    for role, spec in models.items():
        seen = f"verified {spec.verified}" if spec.verified else "NOT VERIFIED"
        print(f"{role:>12}: {spec.name} ({spec.provider}/{spec.model}), {seen}")
    print(f"Rough cost: USD {cost:.2f}")
    pace = suggested_interval(models)
    if pace is not None:
        minutes = (transformations + readings) * pace / 60
        print(
            f"Declared rate limits allow --interval {pace} "
            f"(~{minutes:.0f} min instead of {(transformations + readings) * 6.2 / 3600:.1f} h)"
        )
    if cost > config.get("cost_limit_hint", 15):
        print("Note: this exceeds the USD 15 reservation cap; run it in groups.")
    return models


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="experiment config under configs/")
    parser.add_argument("--transformer", help="override the config's transformer model name")
    parser.add_argument("--extractor", help="override the config's extractor model name")
    parser.add_argument("--resume", type=Path, help="an existing run directory")
    parser.add_argument("--check", action="store_true", help="print size and cost, spend nothing")
    parser.add_argument("--list-models", action="store_true", help="print the model registry")
    parser.add_argument(
        "--allow-unverified-model",
        action="store_true",
        help="spend on a model nobody has called through this code yet",
    )
    parser.add_argument("--limit-usd", type=float, default=15)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stage", choices=("all", "generate", "read"), default="all")
    parser.add_argument(
        "--group", default="all", help="restrict to one corpus group, e.g. statutory"
    )
    parser.add_argument(
        "--interval", type=float, default=6.2, help="minimum seconds between API starts"
    )
    args = parser.parse_args()

    if args.list_models:
        for name, spec in registry().items():
            seen = f"verified {spec.verified}" if spec.verified else "unverified"
            print(f"{name:<14} {spec.provider:<10} {spec.model:<32} {seen}")
        raise SystemExit(0)

    if args.resume:
        execute(ROOT, args.resume, args.workers, args.stage, args.group, args.interval)
        raise SystemExit(0)

    run_config = load_config(ROOT, args.config)
    overrides = {
        role: name
        for role, name in (("transformer", args.transformer), ("extractor", args.extractor))
        if name
    }
    if overrides:
        run_config["models"] = {**(run_config.get("models") or {}), **overrides}
    chosen = estimate(run_config)
    risky = unverified(chosen)
    if risky:
        print(f"\nWARNING: never called through this code: {', '.join(s.name for s in risky)}.")
        print(
            "Run scripts/investigations/check_provider.py first, or pass --allow-unverified-model."
        )
    if args.check:
        raise SystemExit(0)
    if risky and not args.allow_unverified_model:
        raise SystemExit(1)

    directory = create(ROOT, args.limit_usd, config=run_config)
    print("ARTIFACTS", directory, flush=True)
    execute(ROOT, directory, args.workers, args.stage, args.group, args.interval)
