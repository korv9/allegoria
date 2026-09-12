"""Compare models in both roles, across providers, on the project's real prompts.

    python scripts/investigations/compare_models.py --check      # size and cost, no calls
    python scripts/investigations/compare_models.py

A model-selection probe, not an experiment: it runs outside the frozen design,
has no preregistration, and is saved under `data/local/probes/` where it cannot
be mistaken for a run. It goes through the pipeline's own request path, so it
also exercises the provider seam it is measuring.

What it measures, and why each part is here:

- **As a writer**, on one paraphrase and one allegory per source: does the model
  follow the instruction, and how much does the text grow or shrink?
- **As a reader of a source text**, where the answer is known: every slot was
  annotated from that exact text, so every slot should come back `present` with a
  quote that is a verbatim substring. A reader failing here is failing the easy case.
- **As a reader of an allegory**, where there is no ground truth: this measures
  agreement and discrimination, not accuracy. The interesting cell is the one
  allegory where the duty became a mere possibility -- a reader that answers
  `present` to everything cannot see the effect this study measures.

Readers are never told which model wrote a text.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import yaml

from simulacria.generation.models import by_name
from simulacria.generation.provider import (
    api_key,
    billed_cost,
    post_response,
    request_payload,
    response_text,
    with_schema,
)
from simulacria.measurement.corpus import load_corpus
from simulacria.measurement.slot_reading import reading_format, reading_input, validate_reading
from simulacria.providers.base import UnusableResponse

ROOT = Path(__file__).resolve().parents[2]

WRITERS = ["sonnet-5", "gpt-5-4-mini", "gpt-5-4-nano"]
READERS = ["opus-5", "haiku-4-5", "gpt-5-4-mini", "gpt-5-4-nano"]
STYLES = [("paraphrase", "a"), ("allegorize", "a")]
# Allegories are the hard reading case, so only those are read back. Reading
# every writer's every style would quadruple the cost for no extra judgement.
READ_BACK_STYLE = "allegorize"


def call(directory: Path, label: str, model: str, payload: dict, keys: dict) -> dict:
    spec = by_name(model)
    started = time.perf_counter()
    row = {"label": label, "model": model, "provider": spec.provider, "wire_model": spec.model}
    try:
        status, raw = post_response(payload, keys[spec.provider])
    except OSError as error:
        row.update(ok=False, error=f"{type(error).__name__}")
        return row
    name = uuid4().hex
    (directory / f"{name}.json").write_bytes(raw)
    row.update(
        http=status,
        raw=name,
        raw_sha256=sha256(raw).hexdigest(),
        seconds=round(time.perf_counter() - started, 1),
        usd=billed_cost(raw, spec),
    )
    if status != 200:
        row.update(ok=False, error=raw[:160].decode("utf-8", "replace"))
        return row
    try:
        text, response = response_text(raw, spec)
    except UnusableResponse as unusable:
        row.update(ok=False, unusable=unusable.reason)
        return row
    except ValueError as error:
        row.update(ok=False, error=f"{type(error).__name__}: {error}")
        return row
    row.update(
        ok=True,
        text=text,
        usage=response.get("usage"),
        input_tokens=(response.get("usage") or {}).get("input_tokens"),
        output_tokens=(response.get("usage") or {}).get("output_tokens"),
    )
    return row


def read_text(directory, label, model, text, source, keys) -> dict:
    payload = with_schema(
        request_payload(
            by_name(model),
            (ROOT / "prompts/sv/read_slots.txt").read_text(encoding="utf-8"),
            reading_input(text, source["slots"]),
        ),
        reading_format(source["slots"]),
    )
    row = call(directory, label, model, payload, keys)
    if row.get("ok"):
        try:
            slots = validate_reading(row["text"], text, source["slots"])
            row.update(
                valid=True,
                statuses={s["slot_id"]: s["status"] for s in slots},
                present=sum(s["status"] == "present" for s in slots),
                slots=len(slots),
            )
        except (ValueError, KeyError, TypeError) as error:
            row.update(valid=False, invalid_reason=str(error)[:120])
    return row


def main(dry_run: bool) -> None:
    sources = load_corpus(ROOT / "corpus/law_probe_v1.yaml", ROOT)
    prompts = yaml.safe_load((ROOT / "prompts/sv/transform.yaml").read_text(encoding="utf-8"))
    writes = len(WRITERS) * len(sources) * len(STYLES)
    reads = len(READERS) * len(sources) * (1 + len(WRITERS))  # sources + one allegory per writer
    print(f"{writes} transformations + {reads} readings = {writes + reads} calls")
    if dry_run:
        rough = sum(
            by_name(m).cost(700, 400) for m in WRITERS for _ in range(len(sources) * len(STYLES))
        ) + sum(by_name(m).cost(1300, 500) for m in READERS for _ in range(len(sources) * 4))
        print(f"rough cost: USD {rough:.2f} (measured token means, not a quote)")
        return

    keys = {
        p: api_key(ROOT, next(by_name(m) for m in WRITERS + READERS if by_name(m).provider == p))
        for p in {by_name(m).provider for m in WRITERS + READERS}
    }
    directory = ROOT / "data/local/probes" / ("model-comparison-" + uuid4().hex[:12])
    directory.mkdir(parents=True)
    rows: list[dict] = []

    for model in WRITERS:
        for source in sources:
            for style, variant in STYLES:
                row = call(
                    directory,
                    f"write:{style}:{source['passage_id']}",
                    model,
                    request_payload(
                        by_name(model), prompts["styles"][style][variant], source["text"]
                    ),
                    keys,
                )
                row["passage_id"] = source["passage_id"]
                row["style"] = style
                if row.get("ok"):
                    row["length_ratio"] = round(len(row["text"]) / len(source["text"]), 2)
                rows.append(row)
                print(
                    f"  wrote {model:<14} {style:<11} {source['passage_id']:<22} "
                    f"{'ok' if row.get('ok') else row.get('error', row.get('unusable'))}"
                )

    by_id = {s["passage_id"]: s for s in sources}
    targets = [
        {"kind": "source", "writer": None, "passage_id": s["passage_id"], "text": s["text"]}
        for s in sources
    ] + [
        {"kind": "allegory", "writer": r["model"], "passage_id": r["passage_id"], "text": r["text"]}
        for r in rows
        if r.get("ok") and r.get("style") == READ_BACK_STYLE
    ]
    for model in READERS:
        for target in targets:
            row = read_text(
                directory,
                f"read:{target['kind']}:{target['passage_id']}",
                model,
                target["text"],
                by_id[target["passage_id"]],
                keys,
            )
            row.update(
                kind=target["kind"], writer=target["writer"], passage_id=target["passage_id"]
            )
            rows.append(row)
            print(
                f"  read  {model:<14} {target['kind']:<9} by {target['writer']!s:<14} "
                f"{target['passage_id']:<22} valid={row.get('valid')} present={row.get('present')}"
            )

    total = sum(r.get("usd", 0) or 0 for r in rows)
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "kind": "model_comparison_probe",
                "experiment_data": False,
                "at": datetime.now(UTC).isoformat(),
                "writers": WRITERS,
                "readers": READERS,
                "models": {m: by_name(m).record() for m in set(WRITERS + READERS)},
                "total_usd": total,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\ntotal USD {total:.4f} -> {directory}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="size and cost, spend nothing")
    main(parser.parse_args().check)
