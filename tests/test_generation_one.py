"""Pilot contracts. Synthetic API fixtures stay inside pytest temporary directories."""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from simulacria import generation_one
from simulacria.anthropic_io import (
    EXTRACTOR,
    SAMPLING,
    TRANSFORMER,
    api_key,
    request_input,
    request_payload,
    response_text,
    with_schema,
)
from simulacria.generation_report import comparison_rows, latest_run, load_run
from simulacria.measurement.quote_audit import quote_evidence
from simulacria.measurement.slot_reading import reading_input, validate_reading
from simulacria.measurement.source_slots import load_source_slots

ROOT = Path(__file__).resolve().parents[1]


def test_actual_law_sources_and_source_quotes():
    sources = load_source_slots(ROOT / "corpus/law_probe_v1.yaml", ROOT)
    assert len(sources) == 3
    assert sum(len(s["slots"]) for s in sources) == 15
    for source in sources:
        assert all(slot["quote"] in source["text"] for slot in source["slots"])
        assert source["annotation_status"] == "assistant_draft_requires_human_review"


def test_literal_nonmatch_does_not_claim_semantic_loss():
    assert quote_evidence("elva\n timmars vila", "elva timmars vila")["literal_status"] == "found"
    result = quote_evidence("11 timmars vila", "elva timmars vila")
    assert result["literal_status"] == "not_found_requires_review"
    assert result["semantic_status"] == "unreviewed"
    assert (
        quote_evidence("inte elva timmars vila", "elva timmars vila")["semantic_status"]
        == "unreviewed"
    )


def test_blind_reading_has_no_source_or_generation_metadata():
    slot = {"slot_id": "compensation", "quote": "SECRET_SOURCE_QUOTE"}
    payload = json.loads(reading_input("current text", [slot]))
    assert set(payload) == {"text", "schema"}
    assert "SECRET_SOURCE_QUOTE" not in json.dumps(payload)


@pytest.mark.parametrize("mutation", ["quote", "duplicate", "missing", "absent", "status"])
def test_invalid_readings_fail(mutation):
    rows = [{"slot_id": "compensation", "status": "present", "quote": "vila", "note": "textstöd"}]
    if mutation == "quote":
        rows[0]["quote"] = "fabricated"
    elif mutation == "duplicate":
        rows += rows
    elif mutation == "missing":
        rows = []
    else:
        rows[0]["status"] = "absent" if mutation == "absent" else "invented"
    with pytest.raises(ValueError):
        validate_reading(json.dumps({"slots": rows}), "vila", [{"slot_id": "compensation"}])


def test_key_is_loaded_without_being_in_requests(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    (tmp_path / ".env").write_text('LLM_API_KEY="sk-ant-test-only-value"\n')
    assert api_key(tmp_path) == "sk-ant-test-only-value"
    payload = request_payload(TRANSFORMER, "instruction", "text")
    assert "test-only-value" not in json.dumps(payload)
    (tmp_path / ".env").write_text("LLM_API_KEY=\n")
    with pytest.raises(ValueError, match="Set LLM_API_KEY"):
        api_key(tmp_path)
    # A leftover key from another provider must be refused before any request.
    (tmp_path / ".env").write_text('LLM_API_KEY="sk-proj-test-only"\n')
    with pytest.raises(ValueError, match="Anthropic key"):
        api_key(tmp_path)
    with pytest.raises(ValueError, match="pinned"):
        request_payload("unsupported-model", "instruction", "text")


@pytest.mark.parametrize(
    "response",
    [
        {"stop_reason": "max_tokens"},
        {"stop_reason": "refusal"},
        {"stop_reason": "end_turn", "model": "alias"},
        {"stop_reason": "end_turn", "model": TRANSFORMER, "id": "test", "usage": {}, "content": []},
    ],
)
def test_incomplete_or_untraceable_response_is_not_a_generation(response):
    with pytest.raises(ValueError):
        response_text(json.dumps(response).encode(), TRANSFORMER)


@pytest.fixture
def pilot_environment(tmp_path, monkeypatch):
    source = {
        "passage_id": "test-only",
        "text": "vila",
        "source_url": "test-only",
        "text_sha256": sha256(b"vila").hexdigest(),
        "slots": [{"slot_id": "compensation", "kind": "condition", "quote": "vila"}],
    }
    tasks = [
        {
            "passage_id": "test-only",
            "style": "paraphrase",
            "variant": "a",
            "payload": request_payload(TRANSFORMER, "test instruction", "vila"),
        }
    ]
    monkeypatch.setattr(generation_one, "api_key", lambda _root: "test-only")
    monkeypatch.setattr(generation_one, "prepare", lambda _root: ([source], tasks))
    monkeypatch.setattr(generation_one, "code_receipt", lambda _root: {"test_fixture": True})
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts/read_slots.txt").write_text("Test-only reader")
    return tmp_path


def fixture_response(payload, _key):
    text = (
        "vila"
        if payload["model"] == TRANSFORMER
        else json.dumps(
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
    )
    raw = {
        "type": "message",
        "model": payload["model"],
        "id": "response-test-only",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "content": [{"type": "text", "text": text}],
    }
    return 200, json.dumps(raw).encode()


def test_record_and_replay_validates_raw_outputs(pilot_environment, monkeypatch):
    monkeypatch.setattr(generation_one, "post_response", fixture_response)
    path = generation_one.run(pilot_environment)
    run = load_run(path)
    assert run["manifest"]["status"] == "completed"
    assert run["manifest"]["transformer_model"] != run["manifest"]["extractor_model"]
    assert comparison_rows(run)[0]["gen1_reader"] == "present"
    assert comparison_rows(run)[0]["direction"] == "not_computed"
    assert len(run["readings"]) == 2
    received = next(r for r in run["calls"] if r["event"] == "received")
    (path / received["raw_path"]).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="raw response hash"):
        load_run(path)


def test_failed_api_retains_failure_and_no_fake_generation(pilot_environment, monkeypatch):
    monkeypatch.setattr(generation_one, "post_response", lambda *_: (429, b'{"error":"test"}'))
    with pytest.raises(ValueError, match="HTTP 429"):
        generation_one.run(pilot_environment)
    run = load_run(latest_run(pilot_environment))
    assert run["manifest"]["status"] == "failed"
    assert not run["generations"]
    assert any(c["event"] == "failed" for c in run["calls"])
    assert list(latest_run(pilot_environment).glob("raw/*.json"))


def test_no_run_means_no_output(tmp_path):
    with pytest.raises(FileNotFoundError, match="No actual"):
        latest_run(tmp_path)


def test_source_to_child_plan_is_not_a_style_chain():
    sources, tasks = generation_one.prepare(ROOT)
    assert len(tasks) == 24
    by_id = {s["passage_id"]: s["text"] for s in sources}
    assert all(request_input(t["payload"]) == by_id[t["passage_id"]] for t in tasks)
    assert TRANSFORMER != EXTRACTOR


def test_effort_only_reaches_models_that_accept_it():
    """Haiku 4.5 answers `effort` with HTTP 400, so a reader payload must not carry it."""
    reader = with_schema(request_payload(EXTRACTOR, "läs", "text"), {"type": "json_schema"})
    assert "effort" not in reader["output_config"]
    assert reader["output_config"]["format"] == {"type": "json_schema"}
    assert "output_config" not in request_payload(EXTRACTOR, "läs", "text")
    assert request_payload(TRANSFORMER, "skriv", "text")["output_config"] == {"effort": "low"}
    assert set(SAMPLING) == {TRANSFORMER, EXTRACTOR}


@pytest.fixture
def selection_projection_input(tmp_path, monkeypatch):
    """Tiny test-only selection files; tests must not depend on ignored local artifacts."""
    from dataclasses import replace

    import duckdb

    from simulacria.selection.pools import POOLS
    from simulacria.selection.tables import TABLE_NAMES

    tables = tmp_path / "selection-fixture"
    tables.mkdir()
    with duckdb.connect() as connection:
        for name in TABLE_NAMES:
            destination = (tables / f"{name}.parquet").as_posix().replace("'", "''")
            connection.execute(f"COPY (SELECT 1 AS fixture_id) TO '{destination}' (FORMAT PARQUET)")
    monkeypatch.setitem(POOLS, "v1", replace(POOLS["v1"], tables_dir=tables))


def test_sql_projection_lineage_and_rollback(
    pilot_environment, monkeypatch, selection_projection_input
):
    import duckdb

    from simulacria.analysis import build_database

    monkeypatch.setattr(generation_one, "post_response", fixture_response)
    path = generation_one.run(pilot_environment)
    database = pilot_environment / "analysis.duckdb"
    counts = build_database(pilot_environment, database)
    assert counts["texts"] == 2
    assert counts["slot_observations"] == 2
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            "SELECT parent_status, child_status FROM research.slot_comparisons"
        ).fetchall() == [("present", "present")]
        assert (
            connection.execute(
                "SELECT count(*) FROM research.texts c JOIN research.texts p "
                "ON c.run_id=p.run_id AND c.parent_text_id=p.text_id"
            ).fetchone()[0]
            == 1
        )
    (path / "generations.jsonl").write_text("", encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        build_database(pilot_environment, database)
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM research.texts").fetchone()[0] == 2


def test_sql_projection_empty_means_no_runs(tmp_path, selection_projection_input):
    import duckdb

    from simulacria.analysis import build_database

    database = tmp_path / "analysis.duckdb"
    assert build_database(tmp_path, database)["runs"] == 0
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM research.texts").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM selection.provisions").fetchone()[0] == 1
