"""Freezing a run before it costs anything: the design, the manifest, the sources.

`create` writes what a run *means* -- which passages, which instructions, which
prediction and amendments were current -- and hashes it. `execute` refuses to
touch a directory whose design no longer matches that hash, so a run cannot
quietly change what it was testing halfway through.

No API call happens in this module.
"""

import json
from pathlib import Path
from uuid import uuid4

from simulacria.generation.models import resolve as resolve_models
from simulacria.generation.models import sampling
from simulacria.generation.plan import digest, load_config, plan, reader_instruction
from simulacria.generation.receipts import append, code_receipt, timestamp
from simulacria.reporting.runs import jsonl


def ended_chains(directory: Path) -> set[str]:
    """Chains whose transformation produced a refusal or truncation, as recorded.

    That outcome is permanent. Retrying on resume until the model complies would
    replace a refusal with a success and bias the sample toward passages the model
    found easy -- the failure PROTOCOL.md names under "Record failures".
    """
    return {
        e["chain_id"]
        for e in jsonl(directory / "errors.jsonl")
        if e.get("terminal_scope") == "chain" and e.get("phase") == "transformation"
    }


def create(root: Path, limit: float, depth: int | None = None, config: dict | None = None) -> Path:
    """Freeze one experiment's design on disk. No API call happens here."""
    config = config or load_config(root)
    depth = depth if depth is not None else config["generations"]
    if not 0 < limit <= 15 or not 1 <= depth <= 10:
        raise ValueError("exploratory run maximum: USD 15 and ten generations")
    sources, chains = plan(root, config)
    models = resolve_models(config)
    directory = root / "data/local/runs" / ("recursive-" + uuid4().hex)
    directory.mkdir(parents=True)
    (directory / "raw").mkdir()
    reader = reader_instruction(root, config)
    prediction = (root / config["prediction"]).read_text(encoding="utf-8")
    # Amendments are frozen alongside the original, never merged into it: the
    # original names the models it was written for, and the record must show both.
    amendments = {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted((root / "predictions").glob("*-amendment-*.md"))
    }
    frozen = {
        "config": config,
        "sources": sources,
        "chains": chains,
        "reader": reader,
        "prediction": prediction,
        "amendments": amendments,
    }
    (directory / "design.json").write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "schema_version": 2,
        "run_id": directory.name,
        "status": "prepared",
        "started_at": timestamp(),
        "finished_at": None,
        "generations": depth,
        "experiment_type": "exploratory_recursive",
        "experiment": config["experiment"],
        "config_path": config["config_path"],
        "language": config.get("language"),
        "domains": sorted({s["domain"] for s in sources}),
        "preregistered": False,
        "human_review": "pending",
        "design_sha256": digest(frozen),
        "code": code_receipt(root),
        "transformer_model": models["transformer"].model,
        "extractor_model": models["extractor"].model,
        "models": {role: spec.record() for role, spec in models.items()},
        "sampling": sampling(models),
        "planned_transformations": len(chains) * depth,
        "planned_readings": len(chains) * depth + len(sources),
        "cost_limit_usd": limit,
        "prices_usd_per_million": {spec.model: list(spec.prices) for spec in models.values()},
        "price_date": "2026-09-11",
        "shuffle_seed": 20260911,
        "reserved_usd": 0,
        "usage_cost_estimate_usd": 0,
        "limitations": [
            "one transformer",
            "draft source slots",
            "no human agreement",
            "no validated direction",
            "no committed preregistration",
            "no independent repeated chains",
        ],
    }
    for source in sources:
        append(directory / "sources.jsonl", source)
    save_manifest(directory, manifest)
    return directory


def save_manifest(directory: Path, manifest: dict) -> None:
    """Write the manifest atomically: a half-written manifest is an unreadable run."""
    temporary = directory / "manifest.tmp"
    temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temporary.replace(directory / "manifest.json")
