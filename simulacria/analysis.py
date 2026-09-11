"""Rebuildable SQL projection of verified evidence, never the source of record."""

import json
from pathlib import Path

import duckdb

from simulacria.generation_report import RetiredProviderRun, load_run
from simulacria.selection.tables import TABLE_NAMES

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS research;
CREATE SCHEMA IF NOT EXISTS selection;
CREATE TABLE research.runs (
 run_id VARCHAR PRIMARY KEY, status VARCHAR NOT NULL, started_at VARCHAR NOT NULL,
 manifest JSON NOT NULL, artifact_path VARCHAR NOT NULL);
CREATE TABLE research.texts (
 run_id VARCHAR REFERENCES research.runs(run_id), text_id VARCHAR,
 passage_id VARCHAR NOT NULL, generation INTEGER CHECK(generation >= 0),
 parent_text_id VARCHAR, style VARCHAR, variant VARCHAR,
 text VARCHAR NOT NULL, text_sha256 VARCHAR NOT NULL,
 source_sha256 VARCHAR, source_url VARCHAR, call_id VARCHAR,
 chain_id VARCHAR, norm_group VARCHAR, pair_id VARCHAR,
 PRIMARY KEY(run_id, text_id));
CREATE TABLE research.source_slots (
 run_id VARCHAR, text_id VARCHAR, slot_id VARCHAR, kind VARCHAR,
 attaches_to VARCHAR, quote VARCHAR, annotation_status VARCHAR,
 PRIMARY KEY(run_id, text_id, slot_id),
 FOREIGN KEY(run_id, text_id) REFERENCES research.texts(run_id, text_id));
CREATE TABLE research.readings (
 run_id VARCHAR, call_id VARCHAR, text_id VARCHAR, model VARCHAR NOT NULL,
 response_id VARCHAR NOT NULL, PRIMARY KEY(run_id, call_id),
 FOREIGN KEY(run_id, text_id) REFERENCES research.texts(run_id, text_id));
CREATE TABLE research.slot_observations (
 run_id VARCHAR, call_id VARCHAR, slot_id VARCHAR,
 status VARCHAR CHECK(status IN ('present','absent','uncertain')),
 quote VARCHAR, note VARCHAR, PRIMARY KEY(run_id, call_id, slot_id),
 FOREIGN KEY(run_id, call_id) REFERENCES research.readings(run_id, call_id));
CREATE TABLE research.call_events (
 run_id VARCHAR REFERENCES research.runs(run_id), event_index INTEGER,
 call_id VARCHAR NOT NULL, event VARCHAR NOT NULL, receipt JSON NOT NULL,
 PRIMARY KEY(run_id, event_index));
CREATE VIEW research.slot_comparisons AS
SELECT t.run_id, t.text_id, t.parent_text_id, t.passage_id, t.generation,
 t.chain_id, t.norm_group, t.pair_id, t.style, t.variant,
 s.slot_id, s.kind, s.attaches_to, s.quote AS source_quote,
 before.status AS parent_status, after.status AS child_status,
 after.quote AS child_quote, r.model AS reader_model,
 r.call_id AS reader_call_id, baseline.call_id AS parent_reader_call_id,
 original.status AS source_status, after.note AS reader_note,
 runs.status AS run_status, s.annotation_status
FROM research.texts t
JOIN research.runs runs USING(run_id)
JOIN research.texts source ON source.run_id=t.run_id AND source.passage_id=t.passage_id
 AND source.generation=0
JOIN research.source_slots s ON s.run_id=t.run_id AND s.text_id=source.text_id
LEFT JOIN research.readings r ON r.run_id=t.run_id AND r.text_id=t.text_id
LEFT JOIN research.slot_observations after
 ON after.run_id=r.run_id AND after.call_id=r.call_id AND after.slot_id=s.slot_id
LEFT JOIN research.readings baseline
 ON baseline.run_id=t.run_id AND baseline.text_id=t.parent_text_id
LEFT JOIN research.slot_observations before
 ON before.run_id=baseline.run_id AND before.call_id=baseline.call_id
 AND before.slot_id=s.slot_id
LEFT JOIN research.readings source_reading ON source_reading.run_id=t.run_id
 AND source_reading.text_id=source.text_id
LEFT JOIN research.slot_observations original ON original.run_id=source_reading.run_id
 AND original.call_id=source_reading.call_id AND original.slot_id=s.slot_id
WHERE t.generation>0;
"""


def insert(connection, table, values):
    placeholders = ",".join("?" for _ in values)
    connection.execute(f"INSERT INTO research.{table} VALUES ({placeholders})", values)


def import_run(connection, path):
    run = load_run(path)  # Verifies source/output hashes and raw model responses.
    manifest = run["manifest"]
    rid = manifest["run_id"]
    if manifest["status"] == "completed":
        if len(run["generations"]) != manifest["planned_transformations"]:
            raise ValueError("completed run is missing generations")
        if len(run["readings"]) != manifest["planned_readings"]:
            raise ValueError("completed run is missing readings")
    insert(
        connection,
        "runs",
        [
            rid,
            manifest["status"],
            manifest["started_at"],
            json.dumps(manifest),
            str(path.resolve()),
        ],
    )
    source_ids = {}
    for source in run["sources"]:
        pid = source["passage_id"]
        sid = "source:" + pid
        source_ids[pid] = sid
        insert(
            connection,
            "texts",
            [
                rid,
                sid,
                pid,
                0,
                None,
                None,
                None,
                source["text"],
                source["text_sha256"],
                source.get("source_sha256"),
                source["source_url"],
                None,
                None,
                source.get("group", "statutory"),
                source.get("pair_id"),
            ],
        )
        for slot in source["slots"]:
            insert(
                connection,
                "source_slots",
                [
                    rid,
                    sid,
                    slot["slot_id"],
                    slot["kind"],
                    slot.get("attaches_to"),
                    slot["quote"],
                    source.get("annotation_status"),
                ],
            )
    for gen in run["generations"]:
        source = next(s for s in run["sources"] if s["passage_id"] == gen["passage_id"])
        if manifest.get("schema_version") != 2 and (
            gen["generation"] != 1 or gen["parent_generation"] != 0
        ):
            raise ValueError("legacy run format supports only generation one")
        insert(
            connection,
            "texts",
            [
                rid,
                gen["text_id"],
                gen["passage_id"],
                gen["generation"],
                gen.get("parent_text_id", source_ids[gen["passage_id"]]),
                gen["style"],
                gen["variant"],
                gen["text"],
                gen["text_sha256"],
                None,
                None,
                gen["call_id"],
                gen.get("chain_id"),
                source.get("group", "statutory"),
                source.get("pair_id"),
            ],
        )
    for reading in run["readings"]:
        tid = (
            source_ids[reading["passage_id"]] if reading["generation"] == 0 else reading["text_id"]
        )
        insert(
            connection,
            "readings",
            [rid, reading["call_id"], tid, reading["model"], reading["response_id"]],
        )
        for slot in reading["slots"]:
            insert(
                connection,
                "slot_observations",
                [
                    rid,
                    reading["call_id"],
                    slot["slot_id"],
                    slot["status"],
                    slot["quote"],
                    slot["note"],
                ],
            )
    for index, event in enumerate(run["calls"]):
        insert(
            connection,
            "call_events",
            [rid, index, event["call_id"], event["event"], json.dumps(event)],
        )


def build_database(root: Path, destination: Path, pool: str = "v1") -> dict:
    """Transactionally replace derived tables; failed rebuild retains previous data."""
    from simulacria.selection.pools import POOLS

    tables = POOLS[pool].tables_dir
    for name in TABLE_NAMES:
        if not (tables / f"{name}.parquet").is_file():
            raise FileNotFoundError(f"Missing {name}; run scripts/build_tables.py --pool {pool}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(destination))
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute("DROP SCHEMA IF EXISTS research CASCADE")
        connection.execute("DROP SCHEMA IF EXISTS selection CASCADE")
        connection.execute(SCHEMA)
        for name in TABLE_NAMES:
            connection.execute(
                f"CREATE TABLE selection.{name} AS SELECT * FROM read_parquet(?)",
                [str(tables / f"{name}.parquet")],
            )
        for manifest in sorted((root / "data/local/runs").glob("*/manifest.json")):
            try:
                import_run(connection, manifest.parent)
            except RetiredProviderRun as refusal:
                # Excluded, never repaired or approximated. Said out loud so an
                # empty projection cannot be mistaken for "no runs exist".
                print(f"SKIPPED {refusal}", flush=True)
        counts = {
            name: connection.execute(f"SELECT count(*) FROM research.{name}").fetchone()[0]
            for name in ("runs", "texts", "source_slots", "readings", "slot_observations")
        }
        connection.execute("COMMIT")
        return counts
    finally:
        connection.close()
