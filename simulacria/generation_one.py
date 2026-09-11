"""Bounded source-to-generation-one pilot, with append-only API receipts."""

import json
import random
import subprocess
import threading
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import yaml

from simulacria.anthropic_io import (
    EXTRACTOR,
    PRICES,
    SAMPLING,
    TRANSFORMER,
    BudgetExceeded,
    RecordedAPIError,
    UnusableResponse,
    api_key,
    billed_cost,
    estimated_cost,
    post_response,
    request_payload,
    response_text,
    with_schema,
)
from simulacria.measurement.slot_reading import reading_input, validate_reading
from simulacria.measurement.source_slots import load_source_slots
from simulacria.recursive_plan import reading_format

READ_ATTEMPTS = 2

WRITE_LOCK = threading.RLock()


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def append(path: Path, row: dict) -> None:
    with WRITE_LOCK, path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def prepare(root: Path) -> tuple[list[dict], list[dict]]:
    sources = load_source_slots(root / "corpus/law_probe_v1.yaml", root)
    prompts = yaml.safe_load((root / "prompts/generation_one.yaml").read_text(encoding="utf-8"))
    tasks = []
    for source in sources:
        for style, variants in prompts["styles"].items():
            for variant, instruction in variants.items():
                tasks.append(
                    {
                        "passage_id": source["passage_id"],
                        "style": style,
                        "variant": variant,
                        "payload": request_payload(TRANSFORMER, instruction, source["text"]),
                    }
                )
    return sources, tasks


def code_receipt(root: Path) -> dict:
    """Hash actual working files too: an uncommitted pilot must not masquerade as clean git."""
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    paths = [
        p
        for folder in ("simulacria", "prompts")
        for p in (root / folder).rglob("*")
        if p.is_file() and p.suffix in {".py", ".txt", ".yaml"}
    ]
    paths += [root / "corpus/law_probe_v1.yaml", *sorted((root / "predictions").glob("*.md"))]
    return {
        "git_sha": sha,
        "working_tree_dirty": bool(status),
        "files": {
            p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)
        },
    }


def budget_from_calls(run_dir: Path, calls: list[dict], limit: float) -> dict:
    """Rebuild budget state from the receipts alone, for a resumed run.

    `usage_estimate` is what received responses say was consumed. `reserved` holds
    only calls that started and never got a receipt: a request that timed out may
    still have been processed and billed, so its worst-case reservation stays held.
    Every other reservation was settled when its response arrived.
    """
    requests = {c["call_id"]: c for c in calls if c["event"] == "started"}
    received = {c["call_id"]: c for c in calls if c["event"] == "received"}
    usage = 0.0
    for call_id, event in received.items():
        model = requests[call_id]["request"]["model"] if call_id in requests else TRANSFORMER
        usage += billed_cost((run_dir / event["raw_path"]).read_bytes(), model)
    held = sum(c["reserved_usd"] for cid, c in requests.items() if cid not in received)
    return {"limit": limit, "reserved": held, "usage_estimate": usage}


def settle(budget: dict, reservation: float, raw: bytes, model: str) -> None:
    """Replace a call's worst-case hold with what the response says it cost.

    Without this the guard only ever grows: a run whose real spend was $0.068 had
    reserved $0.99, because every call -- including 112 free 429 rejections -- kept
    its full worst-case reservation for good.
    """
    cost = billed_cost(raw, model)
    with WRITE_LOCK:
        budget["reserved"] = max(0.0, budget["reserved"] - reservation)
        budget["usage_estimate"] += cost


def call_recorded(run_dir: Path, payload: dict, key: str, budget: dict) -> tuple[str, dict]:
    reservation = estimated_cost(payload)
    with WRITE_LOCK:
        # Committed spend plus everything still in flight: the limit applies to both.
        if budget["usage_estimate"] + budget["reserved"] + reservation > budget["limit"]:
            raise BudgetExceeded("pilot cost reservation exceeds local USD limit")
        budget["reserved"] += reservation
    call_id = uuid4().hex
    append(
        run_dir / "calls.jsonl",
        {
            "call_id": call_id,
            "event": "started",
            "at": timestamp(),
            "request": payload,
            "reserved_usd": reservation,
        },
    )
    try:
        status, raw = post_response(payload, key)
        # A response arrived, so its cost is now known rather than estimated. A
        # network failure above skips this and leaves the hold in place.
        settle(budget, reservation, raw, payload["model"])
        raw_path = run_dir / "raw" / f"{call_id}.json"
        raw_path.write_bytes(raw)
        append(
            run_dir / "calls.jsonl",
            {
                "call_id": call_id,
                "event": "received",
                "at": timestamp(),
                "http_status": status,
                "raw_path": raw_path.relative_to(run_dir).as_posix(),
                "raw_sha256": sha256(raw).hexdigest(),
            },
        )
        if status != 200:
            raise RecordedAPIError(status, raw)
        text, response = response_text(raw, payload["model"])
        return text, {
            "call_id": call_id,
            "response_id": response["id"],
            "model": response["model"],
            "usage": response["usage"],
            "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Do not serialize exception text: provider/network errors can contain secrets.
        append(
            run_dir / "calls.jsonl",
            {
                "call_id": call_id,
                "event": "failed",
                "at": timestamp(),
                "error_type": type(error).__name__,
            },
        )
        raise


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


def run(root: Path, limit_usd: float = 0.50) -> Path:
    if not 0 < limit_usd <= 0.50:
        raise ValueError("This pilot is limited to at most USD 0.50")
    key = api_key(root)
    sources, tasks = prepare(root)
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
        "preregistered": False,
        "human_review": "pending",
        "generations": 1,
        "transformer_model": TRANSFORMER,
        "extractor_model": EXTRACTOR,
        "sampling": SAMPLING,
        "planned_transformations": len(tasks),
        "planned_readings": len(tasks) + len(sources),
        "prices_usd_per_million": PRICES,
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
        instruction = (root / "prompts/read_slots.txt").read_text(encoding="utf-8")
        flagged = 0
        for row in texts:
            source = by_id[row["passage_id"]]
            payload = request_payload(
                EXTRACTOR, instruction, reading_input(row["text"], source["slots"])
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
