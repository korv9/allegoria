"""Read saved pilot evidence; never synthesize missing model output."""

import json
from hashlib import sha256
from html import escape
from pathlib import Path

from simulacria.anthropic_io import (
    KEY_VARIABLE,
    request_input,
    request_instructions,
    response_text,
    supported,
)
from simulacria.measurement.quote_audit import audit_slots
from simulacria.measurement.slot_reading import reading_input, validate_reading


class RetiredProviderRun(ValueError):
    """A run recorded with models this code no longer decodes.

    Its files stay on disk untouched -- they are evidence that cannot be
    regenerated. What is gone is the ability to replay-verify them here, so they
    are refused by name rather than failing half-way through a parse.
    """


def jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []  # Explicit partial-run output; counts and status remain visible.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def latest_run(root: Path) -> Path:
    manifests = list((root / "data/local/runs").glob("gen1-*/manifest.json"))
    if not manifests:
        raise FileNotFoundError(
            f"No actual generation-one run exists. Add {KEY_VARIABLE} to .env and run "
            "python scripts/run_generation_one.py. No model outputs have been simulated."
        )
    return max(manifests, key=lambda p: json.loads(p.read_text())["started_at"]).parent


def latest_recursive_run(root: Path) -> Path:
    """The newest recursive run this code can verify. Older-provider runs are passed over."""
    readable = []
    for manifest_path in (root / "data/local/runs").glob("recursive-*/manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        models = (manifest.get("transformer_model", ""), manifest.get("extractor_model", ""))
        if all(supported(m) for m in models):
            readable.append((manifest["started_at"], manifest_path.parent))
    if not readable:
        raise FileNotFoundError(
            "No recursive run with the current models exists yet. Run "
            "python scripts/run_recursive.py. No model outputs have been simulated."
        )
    return max(readable)[1]


def load_run(path: Path) -> dict:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    models = (manifest.get("transformer_model", ""), manifest.get("extractor_model", ""))
    if not all(supported(m) for m in models):
        raise RetiredProviderRun(
            f"{path.name} was recorded with {models[0]} / {models[1]}; its raw receipts are "
            "preserved on disk but can no longer be replay-verified by this code"
        )
    sources = jsonl(path / "sources.jsonl")
    generations = jsonl(path / "generations.jsonl")
    readings = jsonl(path / "readings.jsonl")
    calls = jsonl(path / "calls.jsonl")
    recursive = manifest.get("schema_version") == 2
    if recursive:
        from simulacria.recursive_plan import digest

        design = json.loads((path / "design.json").read_text(encoding="utf-8"))
        if digest(design) != manifest["design_sha256"] or sources != design["sources"]:
            raise ValueError("frozen design/source mismatch")
        chains = {c["chain_id"]: c for c in design["chains"]}
    received = {c["call_id"]: c for c in calls if c["event"] == "received"}
    requests = {c["call_id"]: c["request"] for c in calls if c["event"] == "started"}
    source_map = {s["passage_id"]: s for s in sources}
    if len(source_map) != len(sources):
        raise ValueError("duplicate source passage")
    targets = {g["text_id"]: g["text"] for g in generations}
    if len(targets) != len(generations):
        raise ValueError("duplicate generation text ID")
    nodes = {s.get("text_id", "source:" + s["passage_id"]): {**s, "generation": 0} for s in sources}
    nodes.update({g["text_id"]: g for g in generations})
    if len({r["text_id"] for r in readings}) != len(readings):
        raise ValueError("multiple accepted readings for one text")
    if manifest["status"] == "completed":
        if (
            len(generations) != manifest["planned_transformations"]
            or len(readings) != manifest["planned_readings"]
        ):
            raise ValueError("completed run is missing generations or readings")
    for receipt in received.values():
        raw_path = (path / receipt["raw_path"]).resolve()
        if not raw_path.is_relative_to(path.resolve()):
            raise ValueError("raw receipt points outside run")
        if sha256(raw_path.read_bytes()).hexdigest() != receipt["raw_sha256"]:
            raise ValueError("raw response hash mismatch")
    for source in sources:
        if sha256(source["text"].encode("utf-8")).hexdigest() != source["text_sha256"]:
            raise ValueError("saved source text hash mismatch")
    for row in generations + readings:
        receipt = received[row["call_id"]]
        raw_path = (path / receipt["raw_path"]).resolve()
        if not raw_path.is_relative_to(path.resolve()):
            raise ValueError("raw receipt points outside run")
        raw = raw_path.read_bytes()
        if sha256(raw).hexdigest() != receipt["raw_sha256"]:
            raise ValueError("raw response hash mismatch")
        text, response = response_text(raw, row["model"])
        if response["id"] != row["response_id"]:
            raise ValueError("response ID mismatch")
        if sha256(text.encode("utf-8")).hexdigest() != row["text_sha256"]:
            raise ValueError("output text hash mismatch")
        source = source_map[row["passage_id"]]
        if "slots" in row:
            target = source["text"] if row["generation"] == 0 else targets[row["text_id"]]
            if request_input(requests[row["call_id"]]) != reading_input(target, source["slots"]):
                raise ValueError("reading request differs from blind target")
            if recursive and (
                nodes[row["text_id"]]["generation"] != row["generation"]
                or nodes[row["text_id"]]["passage_id"] != row["passage_id"]
            ):
                raise ValueError("reading target metadata mismatch")
            if validate_reading(text, target, source["slots"]) != row["slots"]:
                raise ValueError("saved reading differs from raw response")
        else:
            parent = nodes[row["parent_text_id"]] if recursive else source
            if text != row["text"] or row["parent_sha256"] != parent["text_sha256"]:
                raise ValueError("generation/source lineage mismatch")
            if request_input(requests[row["call_id"]]) != parent["text"]:
                raise ValueError("generation request did not use recorded parent")
            if recursive:
                chain = chains[row["chain_id"]]
                if (
                    row["generation"] != parent["generation"] + 1
                    or row["parent_generation"] != parent["generation"]
                    or row["passage_id"] != parent["passage_id"]
                    or any(row[k] != chain[k] for k in ("passage_id", "style", "variant"))
                    or request_instructions(requests[row["call_id"]]) != chain["instruction"]
                    or (parent["generation"] > 0 and parent["chain_id"] != row["chain_id"])
                ):
                    raise ValueError("recursive chain metadata mismatch")
    return {
        "manifest": manifest,
        "sources": sources,
        "generations": generations,
        "readings": readings,
        "calls": calls,
    }


def comparison_rows(run: dict) -> list[dict]:
    sources = {s["passage_id"]: s for s in run["sources"]}
    readings = {r["text_id"]: r for r in run["readings"]}
    baselines = {r["passage_id"]: r for r in run["readings"] if r["generation"] == 0}
    result = []
    for gen in run["generations"]:
        source = sources[gen["passage_id"]]
        before = {s["slot_id"]: s for s in baselines.get(gen["passage_id"], {}).get("slots", [])}
        after = {s["slot_id"]: s for s in readings.get(gen["text_id"], {}).get("slots", [])}
        for slot in audit_slots(source, gen["text"]):
            a, b = before.get(slot["slot_id"], {}), after.get(slot["slot_id"], {})
            result.append(
                {
                    "passage_id": gen["passage_id"],
                    "style": gen["style"],
                    "variant": gen["variant"],
                    "text_id": gen["text_id"],
                    "slot_id": slot["slot_id"],
                    "kind": slot["kind"],
                    "source_quote": slot["quote"],
                    "literal_status": slot["literal_status"],
                    "gen0_reader": a.get("status", "not_read"),
                    "gen1_reader": b.get("status", "not_read"),
                    "gen1_quote": b.get("quote"),
                    "reader_note": b.get("note"),
                    "human_review": "pending",
                    "direction": "not_computed",
                }
            )
    return result


def side_by_side(source: dict, generation: dict) -> str:
    panels = []
    for title, text in (
        ("Original / generation 0", source["text"]),
        ("Generation 1", generation["text"]),
    ):
        panels.append(
            '<section style="flex:1;min-width:300px;padding:20px;border:1px solid #ccc">'
            f'<h3>{title}</h3><p style="white-space:pre-wrap;line-height:1.7">'
            f"{escape(text)}</p></section>"
        )
    return '<div style="display:flex;flex-wrap:wrap">' + "".join(panels) + "</div>"
