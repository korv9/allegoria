"""How meaning warps across recursive generations -- the signed drift trajectory.

The founding picture: a passage rewritten generation after generation, each child
read blind, and the question is how far and which way its meaning has left the
original. This turns a recorded recursive run into that trajectory.

For every chain and every generation it compares the generation's blinded reading
to the SOURCE reading (generation 0), source-anchored exactly as the reading
bridge requires, and signs the change with the deterministic engine
(`meaningquality`). The output per (chain, generation) is a direction vector
(tightening / loosening / neutral over observable slots) and a net drift
(loosening - tightening); unobservable slots are reported, never counted as
"nothing happened".

    PYTHONPATH=. python scripts/report/warp_trajectory.py --resume data/local/runs/recursive-<id>
    PYTHONPATH=. python scripts/report/warp_trajectory.py            # latest recursive run

No model, no network: it reads a run already on disk. It cannot invent a run --
if none exists, generate one with scripts/run/chains.py first.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from meaningquality.changes import passage_changes, passage_vector, unobservable_reasons
from simulacria.reporting.runs import latest_recursive_run, load_run

ROOT = Path(__file__).resolve().parents[2]


def _slot_map(reading: dict | None) -> dict[str, dict]:
    """A reading's observations keyed by slot_id; empty when the text was not read."""
    return {s["slot_id"]: s for s in (reading or {}).get("slots", [])}


def trajectory(run: dict) -> dict:
    """Per chain, the signed drift of each generation's reading from the source."""
    sources = {s["passage_id"]: s for s in run["sources"]}
    readings = {r["text_id"]: r for r in run["readings"]}
    # The source reading (generation 0) is the anchor every generation is measured
    # against -- cumulative drift from the original, not step to step.
    baselines = {r["passage_id"]: r for r in run["readings"] if r["generation"] == 0}

    chains: dict[str, dict] = {}
    for gen in sorted(run["generations"], key=lambda g: (g["chain_id"], g["generation"])):
        chain = chains.setdefault(
            gen["chain_id"],
            {
                "chain_id": gen["chain_id"],
                "passage_id": gen["passage_id"],
                "style": gen["style"],
                "variant": gen["variant"],
                "points": [],
            },
        )
        reading = readings.get(gen["text_id"])
        if reading is None:
            # Generated but not yet read (a --stage generate run, or a partial one).
            chain["points"].append({"generation": gen["generation"], "read": False})
            continue
        slots = sources[gen["passage_id"]]["slots"]
        before = _slot_map(baselines.get(gen["passage_id"]))
        outcomes = passage_changes(slots, before, _slot_map(reading))
        vec = passage_vector(outcomes)
        chain["points"].append(
            {
                "generation": gen["generation"],
                "read": True,
                "tightening": vec.tightening,
                "loosening": vec.loosening,
                "neutral": vec.neutral,
                "net": vec.loosening - vec.tightening,
                "unobservable": sum(unobservable_reasons(outcomes).values()),
            }
        )
    return {
        "source": f"recursive run {run['manifest']['run_id']}",
        "anchor": "source reading (generation 0); net = loosening - tightening over observable slots",
        "method": "deterministic direction engine (meaningquality) over blinded slot readings; "
        "unobservable slots reported, not counted. No model in the measurement.",
        "chains": list(chains.values()),
    }


def write(report: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "warp_trajectory.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = out_dir / "warp_trajectory.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(
            ["chain_id", "passage_id", "style", "variant", "generation",
             "tightening", "loosening", "neutral", "net", "unobservable"]
        )
        for chain in report["chains"]:
            for pt in chain["points"]:
                if not pt.get("read"):
                    continue
                w.writerow(
                    [chain["chain_id"], chain["passage_id"], chain["style"], chain["variant"],
                     pt["generation"], pt["tightening"], pt["loosening"], pt["neutral"],
                     pt["net"], pt["unobservable"]]
                )
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path, help="a recursive run directory")
    args = parser.parse_args()

    directory = args.resume or latest_recursive_run(ROOT)
    run = load_run(directory)
    report = trajectory(run)
    json_path, csv_path = write(report, ROOT / "review" / date.today().isoformat())

    for chain in report["chains"]:
        read = [p for p in chain["points"] if p.get("read")]
        if not read:
            continue
        last = read[-1]
        arc = " ".join(f"{p['net']:+d}" for p in read)
        print(
            f"{chain['chain_id']} {chain['passage_id']} [{chain['style']}/{chain['variant']}]: "
            f"net drift by gen {arc}  (final {last['net']:+d}, "
            f"{last['unobservable']} slot(s) unobservable)"
        )
    print(f"\nWrote {json_path.relative_to(ROOT)} and {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
