"""Recorded fake API responses here are test fixtures, never experiment artifacts."""

import json
from hashlib import sha256

import pytest

from simulacria.generation import chains, design, receipts
from simulacria.generation.models import by_name
from simulacria.generation.plan import plan
from simulacria.generation.provider import request_input

TRANSFORMER = by_name("sonnet-5").model
from simulacria.reporting.runs import load_run


def test_full_plan_has_expected_matched_chains():
    from pathlib import Path

    sources, chains = plan(Path(__file__).resolve().parents[1])
    assert len(sources) == 33
    assert len(chains) == 84
    assert sum(c["style"] == "paraphrase" for c in chains) == 66
    assert len({s["text_id"] for s in sources}) == 33


@pytest.fixture
def recursive_fixture(experiment_root, monkeypatch):
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
    chain = {
        "chain_id": "test:paraphrase:a",
        "passage_id": "test",
        "style": "paraphrase",
        "variant": "a",
        "instruction": "test-only",
    }
    monkeypatch.setattr(design, "plan", lambda *_: ([source], [chain]))
    monkeypatch.setattr(chains, "api_key", lambda *_: "test-only")
    monkeypatch.setattr(design, "code_receipt", lambda *_: {"test_only": True})
    monkeypatch.setattr(chains, "code_receipt", lambda *_: {"test_only": True})

    requests = []

    def respond(payload, key):
        requests.append(payload)
        if payload["model"] == TRANSFORMER:
            answer = request_input(payload) + " igen"
        else:
            answer = json.dumps(
                {
                    "slots": [
                        {
                            "slot_id": "compensation",
                            "status": "present",
                            "quote": "vila",
                            "note": "test-only",
                        }
                    ]
                }
            )
        raw = {
            "id": "test-only-" + str(len(requests)),
            "type": "message",
            "model": payload["model"],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "content": [{"type": "text", "text": answer}],
        }
        return 200, json.dumps(raw).encode()

    monkeypatch.setattr(receipts, "post_response", respond)
    return tmp_path, requests


def test_recursive_parent_reading_resume_and_tamper(recursive_fixture):
    root, requests = recursive_fixture
    directory = chains.create(root, 1, depth=3)
    chains.execute(root, directory, workers=1, interval=0)
    result = load_run(directory)
    assert result["manifest"]["status"] == "completed"
    assert [g["text"] for g in result["generations"]] == [
        "vila igen",
        "vila igen igen",
        "vila igen igen igen",
    ]
    assert len(result["readings"]) == 4
    assert len(requests) == 7
    chains.execute(root, directory, workers=1, interval=0)
    assert len(requests) == 7
    rows = result["generations"]
    rows[1]["parent_text_id"] = "source:test"
    (directory / "generations.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="lineage"):
        load_run(directory)


def test_quota_failure_is_retained_without_fake_text(recursive_fixture, monkeypatch):
    # An exhausted credit balance is an account-level 400: every later call would
    # fail the same way, so it stops the run. A 429 would instead be retried.
    root, _ = recursive_fixture
    monkeypatch.setattr(
        receipts,
        "post_response",
        lambda *_: (
            400,
            (
                b'{"type":"error","error":{"type":"invalid_request_error",'
                b'"message":"Your credit balance is too low"}}'
            ),
        ),
    )
    directory = chains.create(root, 1, depth=2)
    chains.execute(root, directory, workers=1, interval=0)
    result = load_run(directory)
    assert result["manifest"]["status"] == "partial"
    assert result["generations"] == []
    assert len([c for c in result["calls"] if c["event"] == "started"]) == 1
