"""Bounded source-to-generation-one pilot, with append-only API receipts.

Which passages and which instructions come from an experiment config, so this
runs on any configured corpus. `configs/pilot-sv.yaml` is the default: the three
Swedish statutory passages through every style, for at most USD 0.50.
"""

import json
import random
from pathlib import Path
from uuid import uuid4

from simulacria.generation.models import resolve as resolve_models
from simulacria.generation.models import sampling
from simulacria.generation.plan import PILOT_CONFIG, load_config, plan, reader_instruction
from simulacria.generation.provider import (
    RecordedAPIError,
    UnusableResponse,
    api_key,
    request_payload,
    with_schema,
)
from simulacria.generation.receipts import (
    append,
    call_recorded,
    code_receipt,
    timestamp,
)
from simulacria.measurement.slot_reading import reading_format, reading_input, validate_reading

READ_ATTEMPTS = 2


def prepare(root: Path, config: dict | None = None) -> tuple[list[dict], list[dict]]:
    """The configured passages, and one transformation task per chain."""
    config = config or load_config(root, PILOT_CONFIG)
    sources, chains = plan(root, config)
    transformer = resolve_models(config)["transformer"]
    by_id = {s["passage_id"]: s for s in sources}
    tasks = [
        {
            "passage_id": chain["passage_id"],
            "style": chain["style"],
            "variant": chain["variant"],
            "payload": request_payload(
                transformer, chain["instruction"], by_id[chain["passage_id"]]["text"]
            ),
        }
        for chain in chains
    ]
    return sources, tasks


def read_with_retry(
    run_dir: Path, payload: dict, key: str, budget: dict, row: dict, slots: list[dict]
) -> tuple[list[dict], dict] | None:
    """One text's slot reading: retry, then flag for review. PROTOCOL.md, verbatim.

    A failed extraction is an instrument failure, not an outcome. It is retried
    once, every attempt is recorded, and a text that still fails is flagged rather
    than silently dropped or allowed to end the pilot. Account-level failures --
    the budget, a revoked key, exhausted quota -- still stop everything, because
    every later call would fail the same way.
    """
    context = {
        "phase": "reading",
        "text_id": row["text_id"],
        "passage_id": row["passage_id"],
        "generation": row["generation"],
    }
    for attempt in range(READ_ATTEMPTS):
        call_id = None
        # Anything else call_recorded raises -- the budget, a pinning violation, a
        # response with no ID -- propagates and stops the pilot, as it should.
        try:
            answer, receipt = call_recorded(run_dir, payload, key, budget)
        except RecordedAPIError as error:
            if not error.retryable:
                raise
            reason = f"api_http_{error.status}"
        except UnusableResponse as error:
            reason = f"unusable:{error.reason}"
        except OSError:
            reason = "network"
        else:
            call_id = receipt["call_id"]
            try:
                return validate_reading(answer, row["text"], slots), receipt
            except (ValueError, KeyError, TypeError):
                # The quoted evidence failed validation. The raw answer is on disk.
                reason = "invalid_slot_evidence"
        append(
            run_dir / "errors.jsonl",
            {
                **context,
                "at": timestamp(),
                "attempt": attempt,
                "call_id": call_id,
                "reason": reason,
            },
        )
    append(
        run_dir / "errors.jsonl",
        {**context, "at": timestamp(), "attempts": READ_ATTEMPTS, "reason": "flagged_for_review"},
    )
    return None


def run(root: Path, limit_usd: float = 0.50, config: dict | None = None) -> Path:
    if not 0 < limit_usd <= 0.50:
        raise ValueError("This pilot is limited to at most USD 0.50")
    config = config or load_config(root, PILOT_CONFIG)
    models = resolve_models(config)
    key = api_key(root, models["transformer"])
    sources, tasks = prepare(root, config)
    receipt = code_receipt(root)
    started = timestamp()
    run_dir = root / "data/local/runs" / ("gen1-" + uuid4().hex)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "raw").mkdir()
    manifest = {
        "run_id": run_dir.name,
        "started_at": started,
        "finished_at": None,
        "status": "running",
        "experiment_type": "exploratory_generation_one",
        "experiment": config["experiment"],
        "config_path": config["config_path"],
        "language": config.get("language"),
        "domains": sorted({s["domain"] for s in sources}),
        "preregistered": False,
        "human_review": "pending",
        "generations": 1,
        "transformer_model": models["transformer"].model,
        "extractor_model": models["extractor"].model,
        "models": {role: spec.record() for role, spec in models.items()},
        "sampling": sampling(models),
        "planned_transformations": len(tasks),
        "planned_readings": len(tasks) + len(sources),
        "prices_usd_per_million": {spec.model: list(spec.prices) for spec in models.values()},
        "price_date": "2026-09-11",
        "code": receipt,
        "shuffle_seed": 20260911,
        "cost_limit_usd": limit_usd,
        "limitations": [
            "one transformer",
            "draft source slots",
            "no human agreement",
            "no deterministic direction",
            "no committed preregistration",
        ],
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    budget = {"reserved": 0.0, "usage_estimate": 0.0, "limit": limit_usd}
    by_id = {s["passage_id"]: s for s in sources}
    texts = []
    for source in sources:
        append(run_dir / "sources.jsonl", source)
        texts.append(
            {
                "text_id": uuid4().hex,
                "passage_id": source["passage_id"],
                "generation": 0,
                "text": source["text"],
            }
        )
    try:
        for task in tasks:
            text, response = call_recorded(run_dir, task["payload"], key, budget)
            row = {
                **{k: task[k] for k in ("passage_id", "style", "variant")},
                "text_id": uuid4().hex,
                "generation": 1,
                "parent_generation": 0,
                "parent_sha256": by_id[task["passage_id"]]["text_sha256"],
                "text": text,
                **response,
            }
            append(run_dir / "generations.jsonl", row)
            texts.append(row)
            print(f"generated {task['passage_id']} {task['style']}/{task['variant']}", flush=True)
        random.Random(manifest["shuffle_seed"]).shuffle(texts)
        instruction = reader_instruction(root, config)
        flagged = 0
        for row in texts:
            source = by_id[row["passage_id"]]
            payload = request_payload(
                models["extractor"], instruction, reading_input(row["text"], source["slots"])
            )
            # Structured output constrains syntax only -- a fenced or chatty reply
            # can no longer fail parsing. Whether the quotes are true is still
            # checked by validate_reading below.
            with_schema(payload, reading_format(source["slots"]))
            result = read_with_retry(run_dir, payload, key, budget, row, source["slots"])
            if result is None:
                flagged += 1
                print(f"FLAGGED text {row['text_id']} for review", flush=True)
                continue
            readings, response = result
            append(
                run_dir / "readings.jsonl",
                {
                    "text_id": row["text_id"],
                    "passage_id": row["passage_id"],
                    "generation": row["generation"],
                    "slots": readings,
                    **response,
                },
            )
            print(f"read text {row['text_id']}", flush=True)
        # Not "completed" if any text was flagged: load_run rightly refuses a
        # completed run that is missing readings.
        manifest["status"] = "partial" if flagged else "completed"
        manifest["flagged_readings"] = flagged
    except (OSError, ValueError, KeyError, TypeError) as error:
        manifest["status"] = "failed"
        manifest["error_type"] = type(error).__name__
        print(f"Pilot stopped; retained artifacts: {run_dir}", flush=True)
        raise
    finally:
        manifest.update(
            finished_at=timestamp(),
            reserved_usd=budget["reserved"],
            usage_cost_estimate_usd=budget["usage_estimate"],
        )
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return run_dir
