"""Recorded, resumable recursive chains. No generation ever uses a fabricated parent."""

import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from simulacria.anthropic_io import (
    EXTRACTOR,
    PRICES,
    SAMPLING,
    TRANSFORMER,
    RecordedAPIError,
    UnusableResponse,
    api_key,
    request_payload,
    supported,
    with_schema,
)
from simulacria.generation_one import (
    append,
    budget_from_calls,
    call_recorded,
    code_receipt,
    timestamp,
)
from simulacria.generation_report import jsonl
from simulacria.measurement.slot_reading import reading_input, validate_reading
from simulacria.recursive_plan import digest, plan, reading_format

# Returned by request() when a response arrived but carried no usable text. Not
# None: None means "stopped", and the two must be told apart by the caller.
UNUSABLE = object()


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


def create(root: Path, limit: float, depth: int = 10) -> Path:
    if not 0 < limit <= 15 or not 1 <= depth <= 10:
        raise ValueError("exploratory run maximum: USD 15 and ten generations")
    sources, chains = plan(root)
    directory = root / "data/local/runs" / ("recursive-" + uuid4().hex)
    directory.mkdir(parents=True)
    (directory / "raw").mkdir()
    reader = (root / "prompts/read_slots.txt").read_text(encoding="utf-8")
    prediction = (root / "predictions/2026-09-11-recursive.md").read_text(encoding="utf-8")
    # Amendments are frozen alongside the original, never merged into it: the
    # original names the models it was written for, and the record must show both.
    amendments = {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted((root / "predictions").glob("*-amendment-*.md"))
    }
    frozen = {
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
        "preregistered": False,
        "human_review": "pending",
        "design_sha256": digest(frozen),
        "code": code_receipt(root),
        "transformer_model": TRANSFORMER,
        "extractor_model": EXTRACTOR,
        "sampling": SAMPLING,
        "planned_transformations": len(chains) * depth,
        "planned_readings": len(chains) * depth + len(sources),
        "cost_limit_usd": limit,
        "prices_usd_per_million": PRICES,
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
            "philosophy uses paraphrase only",
            "no independent repeated chains",
        ],
    }
    for source in sources:
        append(directory / "sources.jsonl", source)
    save_manifest(directory, manifest)
    return directory


def save_manifest(directory, manifest):
    temporary = directory / "manifest.tmp"
    temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temporary.replace(directory / "manifest.json")


def execute(
    root: Path,
    directory: Path,
    workers: int = 4,
    stage: str = "all",
    group: str = "all",
    interval: float = 6.2,
) -> Path:
    key = api_key(root)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    frozen = json.loads((directory / "design.json").read_text(encoding="utf-8"))
    if digest(frozen) != manifest["design_sha256"]:
        raise ValueError("frozen design changed")
    if not (supported(manifest["transformer_model"]) and supported(manifest["extractor_model"])):
        # A frozen design is pinned to its models. Sending them to another
        # provider would fail at best, and silently re-mean the run at worst.
        raise ValueError(
            f"{directory.name} was created for {manifest['transformer_model']} and "
            f"{manifest['extractor_model']}, which this code no longer supports; start a new run"
        )
    if not 1 <= workers <= 8:
        raise ValueError("use one to eight workers")
    # Validate every existing parent and receipt before resuming a paid experiment.
    from simulacria.generation_report import load_run

    saved = load_run(directory)
    sources = {s["passage_id"]: s for s in frozen["sources"]}
    # Rebuilt from receipts, not from the manifest: interrupted processes may have
    # persisted calls after the last manifest update.
    budget = budget_from_calls(directory, saved["calls"], manifest["cost_limit_usd"])
    ended = ended_chains(directory)
    stop = threading.Event()
    rate_lock = threading.Lock()
    next_request = [0.0]
    append(
        directory / "sessions.jsonl",
        {
            "at": timestamp(),
            "stage": stage,
            "workers": workers,
            "group": group,
            "interval_seconds": interval,
            "code": code_receipt(root),
        },
    )
    manifest.update(status="running", finished_at=None)
    save_manifest(directory, manifest)

    def request(payload, context):
        for attempt in range(3):
            if stop.is_set():
                return None
            with rate_lock:
                delay = max(0, next_request[0] - time.monotonic())
                if delay:
                    time.sleep(delay)
                next_request[0] = time.monotonic() + interval
            if (directory / "STOP").exists():
                stop.set()
                return None
            try:
                return call_recorded(directory, payload, key, budget)
            except (OSError, ValueError, KeyError, TypeError) as error:
                unusable = isinstance(error, UnusableResponse)
                transient = (
                    error.retryable
                    if isinstance(error, RecordedAPIError)
                    else isinstance(error, OSError)
                )
                # Three scopes. Transient: retry. Unusable: this text only -- a
                # refusal or truncation is data about one chain. Anything else is
                # account- or integrity-level and would fail every chain alike.
                if unusable:
                    scope = "chain" if context["phase"] == "transformation" else "attempt"
                else:
                    scope = None if transient else "run"
                append(
                    directory / "errors.jsonl",
                    {
                        **context,
                        "at": timestamp(),
                        "attempt": attempt,
                        "error_type": type(error).__name__,
                        "transient": transient,
                        "terminal_scope": scope,
                        "reason": getattr(error, "reason", None),
                    },
                )
                if unusable:
                    return UNUSABLE
                if not transient:
                    stop.set()
                    return None
                if attempt < 2:
                    time.sleep((5, 20)[attempt])
        return None

    existing = {(g["chain_id"], g["generation"]): g for g in saved["generations"]}

    def transform(chain):
        if chain["chain_id"] in ended:
            return
        parent = sources[chain["passage_id"]]
        for generation in range(1, manifest["generations"] + 1):
            identity = (chain["chain_id"], generation)
            if identity in existing:
                parent = existing[identity]
                continue
            payload = request_payload(
                manifest["transformer_model"], chain["instruction"], parent["text"]
            )
            context = {
                "phase": "transformation",
                "chain_id": chain["chain_id"],
                "generation": generation,
            }
            result = request(payload, context)
            # Either way the chain ends here: no generation is built on a
            # fabricated parent, and a refusal is recorded, not retried.
            if result is None or result is UNUSABLE:
                return
            text, receipt = result
            row = {
                **{k: chain[k] for k in ("chain_id", "passage_id", "style", "variant")},
                "text_id": uuid4().hex,
                "generation": generation,
                "parent_text_id": parent["text_id"],
                "parent_generation": parent["generation"],
                "parent_sha256": parent["text_sha256"],
                "text": text,
                **receipt,
            }
            append(directory / "generations.jsonl", row)
            parent = row
            print(f"GEN {chain['chain_id']} {generation}/{manifest['generations']}", flush=True)

    def read(row):
        slots = sources[row["passage_id"]]["slots"]
        payload = request_payload(
            manifest["extractor_model"], frozen["reader"], reading_input(row["text"], slots)
        )
        with_schema(payload, reading_format(slots))
        context = {"phase": "reading", "text_id": row["text_id"]}
        for attempt in range(2):
            result = request(payload, context)
            if result is None:
                return
            if result is UNUSABLE:
                # A truncated or refused *reading* is an instrument failure, not
                # an outcome: retry, as PROTOCOL.md requires of extraction.
                continue
            answer, receipt = result
            try:
                observations = validate_reading(answer, row["text"], slots)
            except (ValueError, KeyError, TypeError) as error:
                append(
                    directory / "errors.jsonl",
                    {
                        **context,
                        "at": timestamp(),
                        "call_id": receipt["call_id"],
                        "attempt": attempt,
                        "error_type": type(error).__name__,
                        "reason": "invalid_slot_evidence",
                    },
                )
                continue
            append(
                directory / "readings.jsonl",
                {
                    "text_id": row["text_id"],
                    "passage_id": row["passage_id"],
                    "generation": row["generation"],
                    "slots": observations,
                    **receipt,
                },
            )
            print(f"READ {row['text_id']}", flush=True)
            return

    try:
        if stage in {"all", "generate"}:
            chains = list(frozen["chains"])
            if group != "all":
                chains = [c for c in chains if sources[c["passage_id"]]["group"] == group]
            random.Random(manifest["shuffle_seed"]).shuffle(chains)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(transform, chains))
        if stage in {"all", "read"} and not stop.is_set():
            done = {r["text_id"] for r in jsonl(directory / "readings.jsonl")}
            generated = jsonl(directory / "generations.jsonl")
            used = {g["passage_id"] for g in generated}
            texts = [s for pid, s in sources.items() if pid in used] + generated
            random.Random(manifest["shuffle_seed"]).shuffle(texts)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(read, [r for r in texts if r["text_id"] not in done]))
    finally:
        generated = len(jsonl(directory / "generations.jsonl"))
        observed = len(jsonl(directory / "readings.jsonl"))
        complete = (
            generated == manifest["planned_transformations"]
            and observed == manifest["planned_readings"]
        )
        manifest.update(
            status="completed" if complete else "partial",
            finished_at=timestamp(),
            reserved_usd=budget["reserved"],
            usage_cost_estimate_usd=budget["usage_estimate"],
            completed_transformations=generated,
            completed_readings=observed,
            # Chains that ended on a refusal or truncation. They keep the run
            # "partial" forever, which is honest: those generations do not exist.
            ended_chains=len(ended_chains(directory)),
        )
        save_manifest(directory, manifest)
        print(
            f"RUN {directory.name}: {manifest['status']}; generated={generated}; read={observed}",
            flush=True,
        )
    return directory
