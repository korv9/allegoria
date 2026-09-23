"""Sign the direction of a proposed change to a rule, from verbatim debate words.

Reads corpus/claims_v3_proposals.yaml -- real Riksdagen speeches proposing a
whole-part change to an Employment Protection Act rule -- and classifies each
with the deterministic direction engine. This is not a fidelity check: it signs
whether the proposed change would loosen or tighten the norm.

Only whole-part operations are encoded, because their sign is unambiguous
(DIRECTION.md whole-part table). The operation/target annotations are assistant
drafts (see annotation_status). No model, no network.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import yaml

from simulacria.measurement.direction import Part, Presence, SlotChange, classify

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus/claims_v3_proposals.yaml"

OPERATIONS = {
    "exception_inserted": SlotChange.whole_part(Part.EXCEPTION, Presence.INSERTED),
    "exception_removed": SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED),
    "ceiling_inserted": SlotChange.whole_part(Part.CEILING, Presence.INSERTED),
    "ceiling_removed": SlotChange.whole_part(Part.CEILING, Presence.REMOVED),
}


def run() -> dict:
    corpus = yaml.safe_load(CORPUS.read_text(encoding="utf-8"))
    rows = []
    for p in corpus["proposals"]:
        change = OPERATIONS[p["operation"]]
        rows.append(
            {
                "proposal_id": p["proposal_id"],
                "speaker": p["speaker"],
                "party": p["party"],
                "session": p["session"],
                "target": p["target"],
                "operation": p["operation"],
                "direction": classify(change).value,
                "attribution": p.get("attribution"),
                "quote": " ".join(p["quote"].split()),
                "source_url": p["source_url"],
            }
        )
    return {
        "source": corpus["source"],
        "annotation_status": corpus["annotation_status"],
        "method": "verbatim proposal -> whole-part SlotChange -> deterministic sign; no model, no network",
        "proposals": rows,
    }


def write(report: dict) -> tuple[Path, Path]:
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "claims_v3_proposals_results.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = out_dir / "claims_v3_proposals_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["proposal_id", "speaker", "party", "session", "operation", "direction", "target"]
        )
        for r in report["proposals"]:
            writer.writerow(
                [
                    r["proposal_id"],
                    r["speaker"],
                    r["party"],
                    r["session"],
                    r["operation"],
                    r["direction"],
                    r["target"],
                ]
            )
    return json_path, csv_path


def main() -> None:
    report = run()
    json_path, csv_path = write(report)
    for r in report["proposals"]:
        print(
            f"  {r['direction']:<11} {r['speaker']} ({r['party']}, {r['session']}) — {r['operation']}"
        )
    print(f"\nWrote {json_path.relative_to(ROOT)} and {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
