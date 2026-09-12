"""Run resilience: budget settlement, reading retry-then-flag, chain-local outcomes.

Each test here pins one of three defects found in review, so a regression fails
by name. Synthetic API responses are test fixtures, never experiment artifacts.
"""

import json
from hashlib import sha256

import pytest

from simulacria.generation import chains, design, pilot, receipts
from simulacria.generation.models import by_name
from simulacria.generation.provider import (
    RecordedAPIError,
    billed_cost,
    estimated_cost,
    request_input,
    request_instructions,
    request_payload,
)

TRANSFORMER = by_name("sonnet-5").model
EXTRACTOR = by_name("haiku-4-5").model
from simulacria.reporting.runs import jsonl, load_run

GOOD_READING = json.dumps(
    {"slots": [{"slot_id": "compensation", "status": "present", "quote": "vila", "note": "t"}]}
)
RATE_LIMITED = (
    429,
    b'{"type":"error","error":{"type":"rate_limit_error","message":"slow down"}}',
)


def raw(model: str, text: str, stop: str = "end_turn") -> bytes:
    return json.dumps(
        {
            "id": "test-only",
            "type": "message",
            "model": model,
            "stop_reason": stop,
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "content": [{"type": "text", "text": text}],
        }
    ).encode()


# --- 1. Budget: holds are settled, so free rejections cannot exhaust the limit ---


@pytest.fixture
def run_dir(tmp_path):
    (tmp_path / "raw").mkdir()
    return tmp_path


def test_rate_limited_calls_release_their_reservation(run_dir, monkeypatch):
    payload = request_payload(TRANSFORMER, "test-only", "vila", 900)
    # Room for three reservations. The old accounting kept every hold, so the
    # fourth rejected call would have tripped the limit despite costing nothing.
    budget = {"limit": estimated_cost(payload) * 3, "reserved": 0.0, "usage_estimate": 0.0}
    monkeypatch.setattr(receipts, "post_response", lambda *_: RATE_LIMITED)
    for _ in range(10):
        with pytest.raises(RecordedAPIError):
            receipts.call_recorded(run_dir, payload, "test-only", budget)
    assert budget == {"limit": budget["limit"], "reserved": 0.0, "usage_estimate": 0.0}


def test_success_is_charged_what_it_used_not_its_reservation(run_dir, monkeypatch):
    payload = request_payload(TRANSFORMER, "test-only", "vila", 900)
    budget = {"limit": 1.0, "reserved": 0.0, "usage_estimate": 0.0}
    monkeypatch.setattr(receipts, "post_response", lambda p, _: (200, raw(p["model"], "x")))
    receipts.call_recorded(run_dir, payload, "test-only", budget)
    assert budget["reserved"] == 0.0
    input_rate, output_rate = by_name("sonnet-5").prices
    assert budget["usage_estimate"] == pytest.approx((10 * input_rate + 10 * output_rate) / 1e6)


def test_network_failure_keeps_its_hold(run_dir, monkeypatch):
    """No response means no proof it was not billed, so the worst case stays held."""

    def unreachable(*_):
        raise OSError("test-only")

    payload = request_payload(TRANSFORMER, "test-only", "vila", 900)
    budget = {"limit": 1.0, "reserved": 0.0, "usage_estimate": 0.0}
    monkeypatch.setattr(receipts, "post_response", unreachable)
    with pytest.raises(OSError):
        receipts.call_recorded(run_dir, payload, "test-only", budget)
    assert budget["reserved"] == pytest.approx(estimated_cost(payload))


def test_resume_holds_only_calls_that_never_got_a_receipt(run_dir):
    payload = request_payload(TRANSFORMER, "test-only", "vila", 900)
    (run_dir / "raw/a.json").write_bytes(RATE_LIMITED[1])
    (run_dir / "raw/b.json").write_bytes(raw(TRANSFORMER, "x"))
    calls = [
        {"call_id": cid, "event": "started", "request": payload, "reserved_usd": 0.01}
        for cid in ("a", "b", "c")
    ] + [
        {"call_id": "a", "event": "received", "raw_path": "raw/a.json"},
        {"call_id": "b", "event": "received", "raw_path": "raw/b.json"},
    ]
    budget = receipts.budget_from_calls(run_dir, calls, 15)
    assert budget["reserved"] == pytest.approx(0.01)  # only "c", which never answered
    assert budget["usage_estimate"] == pytest.approx(
        billed_cost(raw(TRANSFORMER, "x"), TRANSFORMER)
    )


def test_billed_cost_counts_truncations_and_survives_gateway_pages():
    assert billed_cost(b"<html>502 Bad Gateway</html>", TRANSFORMER) == 0.0
    assert billed_cost(RATE_LIMITED[1], TRANSFORMER) == 0.0
    assert billed_cost(raw(TRANSFORMER, "x", stop="max_tokens"), TRANSFORMER) > 0


# --- 2. Generation one: a bad reading is retried, then flagged, never fatal ---


@pytest.fixture
def pilot_environment(experiment_root, monkeypatch):
    tmp_path = experiment_root
    source = {
        "passage_id": "test-only",
        "domain": "inline",
        "text": "vila",
        "source_url": "test-only",
        "text_sha256": sha256(b"vila").hexdigest(),
        "slots": [
            {
                "slot_id": "compensation",
                "kind": "condition",
                "quote": "vila",
                "question": "Finns kompensation?",
            }
        ],
    }
    task = {
        "passage_id": "test-only",
        "style": "paraphrase",
        "variant": "a",
        "payload": request_payload(TRANSFORMER, "test-only", "vila"),
    }
    monkeypatch.setattr(pilot, "api_key", lambda *_: "test-only")
    monkeypatch.setattr(pilot, "prepare", lambda *_: ([source], [task]))
    monkeypatch.setattr(pilot, "code_receipt", lambda *_: {"test_only": True})
    return tmp_path


def scripted_reader(monkeypatch, answers):
    """Transformer echoes the source; the reader answers from a script, in order."""
    queue, seen = list(answers), []

    def respond(payload, _key):
        seen.append(payload)
        if payload["model"] == TRANSFORMER:
            return 200, raw(TRANSFORMER, "vila")
        return 200, raw(EXTRACTOR, queue.pop(0))

    monkeypatch.setattr(receipts, "post_response", respond)
    return seen


def test_invalid_reading_is_retried_then_accepted(pilot_environment, monkeypatch):
    # Two texts to read. The first answer is not JSON; its retry succeeds.
    scripted_reader(monkeypatch, ["```json\nnot json\n```", GOOD_READING, GOOD_READING])
    run = load_run(pilot.run(pilot_environment))
    assert run["manifest"]["status"] == "completed"
    assert len(run["readings"]) == 2
    errors = jsonl(run_directory(pilot_environment) / "errors.jsonl")
    assert [e["reason"] for e in errors] == ["invalid_slot_evidence"]


def test_persistent_bad_readings_are_flagged_and_the_pilot_finishes(pilot_environment, monkeypatch):
    scripted_reader(monkeypatch, ["not json"] * 4)
    path = pilot.run(pilot_environment)  # must not raise
    run = load_run(path)
    assert run["manifest"]["status"] == "partial"
    assert run["manifest"]["flagged_readings"] == 2
    assert run["readings"] == []
    reasons = [e["reason"] for e in jsonl(path / "errors.jsonl")]
    assert reasons.count("flagged_for_review") == 2
    assert reasons.count("invalid_slot_evidence") == 4


def test_generation_one_reader_requests_structured_output(pilot_environment, monkeypatch):
    seen = scripted_reader(monkeypatch, [GOOD_READING, GOOD_READING])
    pilot.run(pilot_environment)
    readers = [p for p in seen if p["model"] == EXTRACTOR]
    assert readers and all(p["output_config"]["format"]["type"] == "json_schema" for p in readers)


def run_directory(root):
    return next((root / "data/local/runs").iterdir())


# --- 3. Recursive: a refusal ends its own chain, is recorded, and is not retried ---


@pytest.fixture
def two_chains(experiment_root, monkeypatch):
    tmp_path = experiment_root
    source = {
        "text_id": "source:test",
        "passage_id": "test",
        "domain": "inline",
        "generation": 0,
        "text": "vila",
        "text_sha256": sha256(b"vila").hexdigest(),
        "source_url": "test-only",
        "slots": [
            {
                "slot_id": "compensation",
                "quote": "vila",
                "kind": "condition",
                "question": "Finns kompensation?",
            }
        ],
    }
    planned = [
        {"chain_id": f"test:paraphrase:{v}", "passage_id": "test", "style": "paraphrase",
         "variant": v, "instruction": instruction}
        for v, instruction in (("a", "refuses-at-two"), ("b", "complies"))
    ]  # fmt: skip
    monkeypatch.setattr(design, "plan", lambda *_: ([source], planned))
    monkeypatch.setattr(chains, "api_key", lambda *_: "test-only")
    monkeypatch.setattr(design, "code_receipt", lambda *_: {"test_only": True})
    monkeypatch.setattr(chains, "code_receipt", lambda *_: {"test_only": True})
    seen = []

    def respond(payload, _key):
        seen.append(payload)
        if payload["model"] == EXTRACTOR:
            return 200, raw(EXTRACTOR, GOOD_READING)
        text = request_input(payload)
        if request_instructions(payload) == "refuses-at-two" and text == "vila igen":
            return 200, raw(TRANSFORMER, "", stop="refusal")
        return 200, raw(TRANSFORMER, text + " igen")

    monkeypatch.setattr(receipts, "post_response", respond)
    return tmp_path, seen


def test_refusal_ends_one_chain_without_stopping_the_run(two_chains):
    root, _ = two_chains
    directory = chains.create(root, 1, depth=3)
    chains.execute(root, directory, workers=1, interval=0)
    run = load_run(directory)
    by_chain = {}
    for g in run["generations"]:
        by_chain.setdefault(g["chain_id"], []).append(g["generation"])
    assert sorted(by_chain["test:paraphrase:b"]) == [1, 2, 3]  # the other chain finished
    assert by_chain["test:paraphrase:a"] == [1]  # the refusing chain stopped at its refusal
    # The read stage ran, which it would not have if the refusal had set `stop`.
    assert len(run["readings"]) == 1 + 4
    terminal = [e for e in jsonl(directory / "errors.jsonl") if e.get("terminal_scope")]
    assert [(e["chain_id"], e["reason"], e["terminal_scope"]) for e in terminal] == [
        ("test:paraphrase:a", "refusal", "chain")
    ]
    assert run["manifest"]["ended_chains"] == 1
    assert run["manifest"]["status"] == "partial"


def test_resume_does_not_retry_a_refused_chain(two_chains):
    root, seen = two_chains
    directory = chains.create(root, 1, depth=3)
    chains.execute(root, directory, workers=1, interval=0)
    before = len(seen)
    chains.execute(root, directory, workers=1, interval=0)
    # Retrying until the model complies would swap a recorded refusal for a
    # success and bias the sample toward passages the model found easy.
    assert len(seen) == before
