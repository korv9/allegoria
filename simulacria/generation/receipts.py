"""Append-only API receipts, and the USD budget they settle.

Every paid attempt is written down before it is made and again when it answers,
with the raw bytes on disk and their hash in the record. The budget reserves a
worst case before each call and replaces that hold with the response's actual
billed cost, so a run cannot be stopped by holds it no longer owes.

A call that never got a receipt keeps its hold: with no response there is no
proof it was not processed and billed.
"""

import json
import subprocess
import threading
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from simulacria.generation.provider import (
    BudgetExceeded,
    billed_cost,
    estimated_cost,
    post_response,
    recorded_error,
    response_text,
)

WRITE_LOCK = threading.RLock()


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def append(path: Path, row: dict) -> None:
    with WRITE_LOCK, path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def _claimed(raw: bytes) -> str:
    """The model a saved response says it is. Empty when the bytes are not JSON."""
    try:
        return str(json.loads(raw).get("model", ""))
    except (ValueError, AttributeError):
        return ""


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
        raw = (run_dir / event["raw_path"]).read_bytes()
        # Which model was billed comes from the request that started the call.
        # Without one -- a receipt whose request line was lost -- the response's
        # own claim is used, and an undeclared model costs zero rather than
        # silently being priced as something else.
        model = requests[call_id]["request"]["model"] if call_id in requests else _claimed(raw)
        usage += billed_cost(raw, model)
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
            raise recorded_error(status, raw, payload["model"])
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
    paths += [
        *sorted((root / "corpus").glob("*.yaml")),
        *sorted((root / "configs").glob("*.yaml")),
        *sorted((root / "predictions").glob("*.md")),
    ]
    return {
        "git_sha": sha,
        "working_tree_dirty": bool(status),
        "files": {
            p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)
        },
    }
