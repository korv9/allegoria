"""Spår 1: measure signed drift across real successive VERSIONS of a rule.

The founding question -- does meaning drift have a sign? -- without an LLM. The
transformer is not a model here; it is history: a provision is amended, and the
engine signs each version-to-version change. Measurement was always model-free,
so with real versions in and a deterministic classifier, the whole pipeline is
LLM-free.

Reads corpus/versions_v1.yaml (an ordered version chain per LAS provision, each
version carrying the slot's magnitude and the source lydelse) and classifies each
consecutive change with the numeric ceiling metric in direction.py. Current values
are quoted verbatim from the committed source text (data/source/sfs/sfs-1982-80.txt,
lagen.nu); historical before-values cite the amending SFS act and proposition.

The 2022 arbetsrättsreform (SFS 2022:835) is the clean case: it *loosened* the
turordning exemption (22 §: 2 -> 3 workers) yet *tightened* fixed-term employment
(5 a §: 24 -> 12 months before mandatory conversion) -- one reform, opposite signs
on different provisions, which is exactly what a signed metric can show.

    PYTHONPATH=. python scripts/investigations/version_drift.py

Writes review/<date>/sfs_drift.{json,csv}. No model; reads committed text only.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import yaml

from simulacria.measurement.direction import SlotChange, classify

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus/versions_v1.yaml"


def drift_for(slot: dict, versions: list[dict]) -> list[dict]:
    """Sign each consecutive version transition for one provision's slot."""
    transitions = []
    for before, after in zip(versions, versions[1:]):
        if slot["kind"] == "bound":
            change = SlotChange.ceiling_bound(before["magnitude"], after["magnitude"])
        else:
            raise ValueError(f"version drift not implemented for slot kind {slot['kind']!r}")
        transitions.append(
            {
                "from": before["label"],
                "to": after["label"],
                "before": before["magnitude"],
                "after": after["magnitude"],
                "status": after.get("status"),
                "direction": classify(change).value,
                "quote_before": " ".join((before.get("quote") or "").split()),
                "quote_after": " ".join((after.get("quote") or "").split()),
                "verify": after.get("verify"),
            }
        )
    return transitions


def build() -> dict:
    corpus = yaml.safe_load(CORPUS.read_text(encoding="utf-8"))
    provisions = []
    for p in corpus["provisions"]:
        provisions.append(
            {
                "provision_id": p["provision_id"],
                "title": p["title"],
                "unit": p.get("unit", ""),
                "note": " ".join((p.get("note") or "").split()),
                "transitions": drift_for(p["slot"], p["versions"]),
            }
        )
    return {
        "source": " ".join(corpus["source"].split()),
        "annotation_status": corpus["annotation_status"],
        "method": "real successive versions; deterministic numeric-ceiling sign; no model, no network",
        "provisions": provisions,
    }


def write_csv(report: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(
            ["provision_id", "title", "unit", "from", "to", "before", "after",
             "direction", "status"]
        )
        for p in report["provisions"]:
            for t in p["transitions"]:
                w.writerow(
                    [p["provision_id"], p["title"], p["unit"], t["from"], t["to"],
                     t["before"], t["after"], t["direction"], t["status"]]
                )


def main() -> None:
    report = build()
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "sfs_drift.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = out_dir / "sfs_drift.csv"
    write_csv(report, csv_path)
    for p in report["provisions"]:
        print(f"\n{p['provision_id']} — {p['title']}")
        for t in p["transitions"]:
            print(
                f"  {t['direction']:<11} {t['before']} -> {t['after']} {p['unit']}  ({t['status']}: {t['from']} -> {t['to']})"
            )
    print(f"\nWrote {path.relative_to(ROOT)} and {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
