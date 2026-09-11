"""Probe Anthropic models for the transformer and extractor roles. Not an experiment.

    python scripts/investigations/model_probe.py

A model-selection probe on the project's real prompts and sources. It answers
"which model should do which job", and nothing it produces is experiment data:
it runs outside the frozen design, with no preregistration, and is saved under
data/local/probes/ so it can never be mistaken for a run.

Every candidate is tried in BOTH roles, so the recommendation rests on evidence
rather than on the assumption that the bigger model belongs in a given seat.

Extraction is scored against the source text, where the answer is known: every
slot was annotated from that exact text, so every slot should come back present
with a quote that is a verbatim substring of it.

Deliberately NOT used, though the API offers it: server-side refusal fallbacks.
A fallback silently re-runs a refused request on a different model. In this
project a refusal is data (PROTOCOL.md), and a pinned model that quietly becomes
another model is exactly what the manifest exists to rule out.

Needs LLM_API_KEY in the environment or .env. The key is never printed or saved.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import anthropic
import yaml

from simulacria.measurement.slot_reading import reading_input, validate_reading
from simulacria.measurement.source_slots import load_source_slots
from simulacria.recursive_plan import reading_format

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ("claude-sonnet-5", "claude-opus-5")
# USD per million tokens, input / output. Thinking tokens bill as output.
PRICES = {"claude-sonnet-5": (2.00, 10.00), "claude-opus-5": (5.00, 25.00)}
STYLES = (("paraphrase", "a"), ("allegorize", "a"))
TRANSFORM_EFFORT = "low"
EXTRACT_EFFORT = "medium"


def llm_key() -> str:
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key and (ROOT / ".env").is_file():
        for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "LLM_API_KEY":
                key = value.strip().strip("\"'")
    if not key.startswith("sk-ant"):
        raise SystemExit("Set LLM_API_KEY to an Anthropic key in .env or the environment")
    return key


def cost(model: str, usage) -> float:
    input_rate, output_rate = PRICES[model]
    return (usage.input_tokens * input_rate + usage.output_tokens * output_rate) / 1_000_000


def call(client, directory: Path, label: str, **params) -> dict:
    """One recorded request. Failures are rows in the result, not crashes."""
    started = time.perf_counter()
    row = {"label": label, "model_requested": params["model"]}
    try:
        message = client.messages.create(**params)
    except anthropic.APIStatusError as error:
        row.update(ok=False, error=f"HTTP {error.status_code}: {error.message}"[:300])
        return row
    except anthropic.APIConnectionError:
        row.update(ok=False, error="connection error")
        return row
    (directory / f"{uuid4().hex}.json").write_text(message.to_json(), encoding="utf-8")
    text = "".join(b.text for b in message.content if b.type == "text")
    row.update(
        ok=message.stop_reason == "end_turn",
        model_returned=message.model,
        stop_reason=message.stop_reason,
        seconds=round(time.perf_counter() - started, 1),
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        usd=cost(params["model"], message.usage),
        text=text,
    )
    return row


def readers_on_allegories(client, probe: Path) -> None:
    """Both readers on every saved allegory: the hard case the first pass skipped.

    Reading the source is easy -- the slots were annotated from it. An allegory
    expresses the same relations figuratively, so a reader must decide between
    present, uncertain and absent, and any quote must come from the allegory.
    There is no ground truth here, so this measures validity and agreement, not
    accuracy. Readers are never shown which model wrote the text.
    """
    manifest = json.loads((probe / "manifest.json").read_text(encoding="utf-8"))
    sources = {
        s["passage_id"]: s for s in load_source_slots(ROOT / "corpus/law_probe_v1.yaml", ROOT)
    }
    reader = (ROOT / "prompts/read_slots.txt").read_text(encoding="utf-8")
    rows = []
    for text_row in manifest["rows"]:
        if not text_row["label"].startswith("transform:allegorize") or not text_row.get("text"):
            continue
        source = sources[text_row["label"].split(":", 2)[2]]
        schema = reading_format(source["slots"])["schema"]
        for model in CANDIDATES:
            row = call(
                client,
                probe,
                f"read-allegory:{text_row['model_requested']}:{source['passage_id']}",
                model=model,
                max_tokens=8000,
                system=reader,
                messages=[
                    {"role": "user", "content": reading_input(text_row["text"], source["slots"])}
                ],
                output_config={
                    "effort": EXTRACT_EFFORT,
                    "format": {"type": "json_schema", "schema": schema},
                },
            )
            row["writer"] = text_row["model_requested"]
            if row.get("text"):
                try:
                    slots = validate_reading(row["text"], text_row["text"], source["slots"])
                    row["valid"] = True
                    row["statuses"] = {s["slot_id"]: s["status"] for s in slots}
                except (ValueError, KeyError, TypeError) as error:
                    row.update(valid=False, invalid_reason=str(error)[:120])
            rows.append(row)
    manifest["allegory_readings"] = rows
    (probe / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(probe)


def main() -> None:
    import sys

    client = anthropic.Anthropic(api_key=llm_key())
    if len(sys.argv) == 3 and sys.argv[1] == "--readers-on":
        readers_on_allegories(client, Path(sys.argv[2]))
        return
    sources = load_source_slots(ROOT / "corpus/law_probe_v1.yaml", ROOT)
    prompts = yaml.safe_load((ROOT / "prompts/generation_one.yaml").read_text(encoding="utf-8"))
    reader = (ROOT / "prompts/read_slots.txt").read_text(encoding="utf-8")

    directory = ROOT / "data/local/probes" / ("model-probe-" + uuid4().hex[:12])
    directory.mkdir(parents=True)
    rows: list[dict] = []

    for model in CANDIDATES:
        # The Models API is the pinning check: what the ID actually resolves to.
        info = client.models.retrieve(model)
        rows.append(
            {
                "label": "models-api",
                "model_requested": model,
                "id": info.id,
                "display_name": info.display_name,
                "created_at": str(info.created_at),
            }
        )
        for source in sources:
            for style, variant in STYLES:
                row = call(
                    client,
                    directory,
                    f"transform:{style}:{source['passage_id']}",
                    model=model,
                    max_tokens=8000,
                    system=prompts["styles"][style][variant],
                    messages=[{"role": "user", "content": source["text"]}],
                    output_config={"effort": TRANSFORM_EFFORT},
                )
                if row.get("text"):
                    row["length_ratio"] = round(len(row["text"]) / len(source["text"]), 2)
                rows.append(row)

            schema = reading_format(source["slots"])["schema"]
            row = call(
                client,
                directory,
                f"extract:{source['passage_id']}",
                model=model,
                max_tokens=8000,
                system=reader,
                messages=[
                    {"role": "user", "content": reading_input(source["text"], source["slots"])}
                ],
                output_config={
                    "effort": EXTRACT_EFFORT,
                    "format": {"type": "json_schema", "schema": schema},
                },
            )
            if row.get("text"):
                try:
                    slots = validate_reading(row["text"], source["text"], source["slots"])
                    row["valid"] = True
                    row["present"] = sum(s["status"] == "present" for s in slots)
                    row["slots"] = len(slots)
                except (ValueError, KeyError, TypeError) as error:
                    row.update(valid=False, invalid_reason=str(error)[:120])
            rows.append(row)

    manifest = {
        "kind": "model_selection_probe",
        "experiment_data": False,
        "at": datetime.now(UTC).isoformat(),
        "candidates": CANDIDATES,
        "prices_usd_per_million": PRICES,
        "transform_effort": TRANSFORM_EFFORT,
        "extract_effort": EXTRACT_EFFORT,
        "temperature": "not settable on these models",
        "refusal_fallbacks": "disabled on purpose: a refusal is data, and the model must stay pinned",
        "rows": rows,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(directory)


if __name__ == "__main__":
    main()
