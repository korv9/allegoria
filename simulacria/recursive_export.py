"""Portable, actual result tables and a blinded review packet from a pinned run."""

import json
import random
from hashlib import sha256
from pathlib import Path

import duckdb

from simulacria.generation_report import load_run
from simulacria.measurement.slot_reading import reading_input
from simulacria.recursive_metrics import law_ordering, observations, planned_coverage


def export_results(directory: Path, destination: Path, database: Path) -> dict:
    run = load_run(directory)
    design = json.loads((directory / "design.json").read_text(encoding="utf-8"))
    destination.mkdir(parents=True, exist_ok=True)
    rid = run["manifest"]["run_id"]
    observation_frame = observations(run)
    frames = {
        "observations": observation_frame,
        "law_ordering": law_ordering(run, design, observation_frame),
        "chain_coverage": planned_coverage(run, design),
    }
    with duckdb.connect(str(database), read_only=True) as connection:
        for table in (
            "runs",
            "texts",
            "source_slots",
            "readings",
            "slot_observations",
            "slot_comparisons",
            "call_events",
        ):
            frames[table] = connection.execute(
                f"SELECT * FROM research.{table} WHERE run_id=?", [rid]
            ).df()
        # Metadata/internal requests stay in the research export, not the public result JSON.
    public = {
        "manifest": {
            k: run["manifest"][k]
            for k in (
                "run_id",
                "status",
                "started_at",
                "generations",
                "transformer_model",
                "extractor_model",
                "planned_transformations",
                "planned_readings",
                "limitations",
                "human_review",
            )
        },
        "sources": run["sources"],
        "generations": run["generations"],
        "readings": run["readings"],
    }
    (destination / "results.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with duckdb.connect() as connection:
        for name, frame in frames.items():
            connection.register("export_frame", frame)
            target = (destination / f"{name}.parquet").as_posix().replace("'", "''")
            connection.execute(f"COPY export_frame TO '{target}' (FORMAT PARQUET)")
            connection.unregister("export_frame")
    sources = {s["passage_id"]: s for s in run["sources"]}
    texts = run["sources"] + run["generations"]
    # All texts, shuffled once; no generation, source type or model answer in the blind packet.
    random.Random(20260911).shuffle(texts)
    blind, key = [], []
    for index, row in enumerate(texts):
        review_id = f"review-{index + 1:04d}"
        payload = json.loads(reading_input(row["text"], sources[row["passage_id"]]["slots"]))
        blind.append({"review_id": review_id, **payload})
        key.append({"review_id": review_id, "text_id": row["text_id"], "run_id": rid})
    for name, rows in (("human_review_blind", blind), ("human_review_key", key)):
        (destination / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
        )
    receipt = {
        "run_id": rid,
        "files": {
            p.name: sha256(p.read_bytes()).hexdigest()
            for p in destination.iterdir()
            if p.is_file() and p.name != "export_manifest.json"
        },
    }
    (destination / "export_manifest.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    return {name: len(frame) for name, frame in frames.items()}
