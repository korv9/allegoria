"""Debate-vs-law proof of concept: sign the gap between how a rule is described
and what the rule says.

Reads corpus/claims_v1.yaml -- a real, slot-annotated SFS provision plus a set of
constructed descriptions of it -- and runs each description through the Allegoria
direction engine (simulacria.measurement.changes). It writes a dated evidence
artifact under review/ and prints a summary.

No model and no network are involved: the slot readings are assistant
hand-annotations carried in the corpus, and the classification is deterministic.
This demonstrates the pipeline end to end; a real study would replace the
hand-annotated readings with a blinded local extractor and measure agreement.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from simulacria.measurement.changes import (
    passage_changes,
    passage_vector,
    unobservable_reasons,
)

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "corpus/claims_v1.yaml")


def verdict(tightening: int, loosening: int, neutral: int) -> str:
    """A human-readable label for one description's count vector."""
    if tightening and loosening:
        return "mixed"
    if tightening:
        return "tightening"
    if loosening:
        return "loosening"
    if neutral:
        return "faithful"
    return "no_observable_change"


def check_quotes(description: dict) -> list[str]:
    """Every present reading must quote the description verbatim, exactly as the
    measurement contract requires of a real extractor."""
    problems = []
    text = " ".join(description["text"].split())
    for slot_id, reading in description["readings"].items():
        quote = reading.get("quote")
        if reading["status"] == "present":
            if not quote or " ".join(quote.split()) not in text:
                problems.append(f"{description['description_id']}/{slot_id}: quote not verbatim")
        elif quote is not None:
            problems.append(
                f"{description['description_id']}/{slot_id}: absent slot carries a quote"
            )
    return problems


def run_description(slots: list[dict], description: dict) -> dict:
    before = {s["slot_id"]: {"status": "present"} for s in slots}
    after = description["readings"]
    outcomes = passage_changes(slots, before, after)
    vector = passage_vector(outcomes)
    return {
        "description_id": description["description_id"],
        "label": description["label"],
        "provenance": description["provenance"],
        "reader": description.get("reader", "determinacy-aware"),
        "speaker": description.get("speaker"),
        "party": description.get("party"),
        "session": description.get("session"),
        "source_url": description.get("source_url"),
        "text": " ".join(description["text"].split()),
        "tightening": vector.tightening,
        "loosening": vector.loosening,
        "neutral": vector.neutral,
        "verdict": verdict(vector.tightening, vector.loosening, vector.neutral),
        "observable_slots": sum(o.observable for o in outcomes),
        "unobservable": unobservable_reasons(outcomes),
        "per_slot": [
            {
                "slot_id": o.slot_id,
                "kind": o.kind,
                "part": o.part.value,
                "observable": o.observable,
                "sign": o.sign.value if o.sign else None,
                "reason": o.reason,
            }
            for o in outcomes
        ],
    }


def build() -> dict:
    corpus = yaml.safe_load(CORPUS.read_text(encoding="utf-8"))
    problems, provisions = [], []
    for provision in corpus["provisions"]:
        results = []
        for description in provision["descriptions"]:
            problems.extend(check_quotes(description))
            results.append(run_description(provision["slots"], description))
        provisions.append(
            {
                "provision_id": provision["provision_id"],
                "title": provision["title"],
                "law_says": " ".join(provision["law_says"].split()),
                "descriptions": results,
            }
        )
    return {
        "generated_from": "corpus/claims_v1.yaml",
        "annotation_status": corpus["annotation_status"],
        "method": "hand-annotated readings; deterministic direction; no model, no network",
        "quote_problems": problems,
        "provisions": provisions,
    }


def write(report: dict) -> tuple[Path, Path]:
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = CORPUS.stem + "_results"
    json_path = out_dir / f"{stem}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = out_dir / f"{stem}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "provision_id",
                "description_id",
                "label",
                "verdict",
                "tightening",
                "loosening",
                "neutral",
                "observable_slots",
                "unobservable_count",
            ]
        )
        for provision in report["provisions"]:
            for row in provision["descriptions"]:
                writer.writerow(
                    [
                        provision["provision_id"],
                        row["description_id"],
                        row["label"],
                        row["verdict"],
                        row["tightening"],
                        row["loosening"],
                        row["neutral"],
                        row["observable_slots"],
                        sum(row["unobservable"].values()),
                    ]
                )
    return json_path, csv_path


def main() -> None:
    report = build()
    json_path, csv_path = write(report)
    for provision in report["provisions"]:
        print(f"\n{provision['provision_id']} — {provision['title']}")
        for row in provision["descriptions"]:
            vec = (row["tightening"], row["loosening"], row["neutral"])
            extra = (
                f"  [{sum(row['unobservable'].values())} unobservable]"
                if row["unobservable"]
                else ""
            )
            print(f"  {row['verdict']:<18} {str(vec):<10} {row['label']}{extra}")
    if report["quote_problems"]:
        print("\nQUOTE PROBLEMS:", report["quote_problems"])
    else:
        print("\nAll present readings quote their description verbatim.")
    print(f"\nWrote {json_path.relative_to(ROOT)} and {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
