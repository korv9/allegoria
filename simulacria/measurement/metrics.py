"""Descriptive tests of recorded slot observations, not normative-direction judgments."""

import pandas as pd

PAIRS = {
    "sfs-2026-1281:K10P10": [("exception_deadline", "exception"), ("deadline_start", "exception")],
    "sfs-1982-673:P13": [
        ("unforeseen_event", "temporary_exception"),
        ("compensation", "temporary_exception"),
    ],
    "sfs-1977-480:P12": [("special_reasons", "exception")],
}


def observations(run: dict) -> pd.DataFrame:
    sources = {s["passage_id"]: s for s in run["sources"]}
    texts = {r["text_id"]: r for r in run["sources"] + run["generations"]}
    readings = {r["text_id"]: r for r in run["readings"]}
    rows = []
    for tid, text in texts.items():
        source = sources[text["passage_id"]]
        slots = {s["slot_id"]: s for s in readings.get(tid, {}).get("slots", [])}
        for slot in source["slots"]:
            observed = slots.get(slot["slot_id"], {})
            rows.append(
                {
                    "text_id": tid,
                    "passage_id": source["passage_id"],
                    "norm_group": source["group"],
                    "pair_id": source.get("pair_id"),
                    "generation": text["generation"],
                    "chain_id": text.get("chain_id"),
                    "style": text.get("style"),
                    "variant": text.get("variant"),
                    "slot_id": slot["slot_id"],
                    "kind": slot["kind"],
                    "attaches_to": slot["attaches_to"],
                    "status": observed.get("status", "not_read"),
                    "quote": observed.get("quote"),
                    "note": observed.get("note"),
                    "reader_call_id": readings.get(tid, {}).get("call_id"),
                }
            )
    return pd.DataFrame(rows)


def first_absence(states: dict, depth: int) -> dict:
    """Do not turn censoring or unresolved observations into exact loss times."""
    if states.get(0) != "present":
        return {"first_absent": None, "timing": "baseline_not_present", "reappeared": False}
    first = next((g for g in range(1, depth + 1) if states.get(g) == "absent"), None)
    end = first if first is not None else depth
    exact = all(states.get(g) in {"present", "absent"} for g in range(1, end + 1))
    timing = "observed" if first is not None else "not_observed_through_depth"
    if not exact:
        timing = "unresolved"
    reappeared = first is not None and any(
        states.get(g) == "present" for g in range(first + 1, depth + 1)
    )
    return {"first_absent": first, "timing": timing, "reappeared": reappeared}


def ordering(qualifier: dict, exception: dict) -> str:
    if qualifier["timing"] in {"unresolved", "baseline_not_present"} or exception["timing"] in {
        "unresolved",
        "baseline_not_present",
    }:
        return "unresolved"
    q, e = qualifier["first_absent"], exception["first_absent"]
    if q is None and e is None:
        return "neither_observed_absent"
    if e is None or (q is not None and q < e):
        return "qualifier_first"
    if q is None or e < q:
        return "exception_first"
    return "same_generation"


def law_ordering(run: dict, design: dict, frame: pd.DataFrame) -> pd.DataFrame:
    depth = run["manifest"]["generations"]
    rows = []
    for chain in design["chains"]:
        pid = chain["passage_id"]
        if pid not in PAIRS:
            continue
        subset = frame[
            (frame.chain_id == chain["chain_id"])
            | ((frame.passage_id == pid) & (frame.generation == 0))
        ]
        for qualifier, exception in PAIRS[pid]:
            events = []
            for slot in (qualifier, exception):
                values = subset[subset.slot_id == slot]
                events.append(first_absence(dict(zip(values.generation, values.status)), depth))
            q, e = events
            rows.append(
                {
                    **{k: chain[k] for k in ("chain_id", "passage_id", "style", "variant")},
                    "qualifier": qualifier,
                    "exception": exception,
                    "ordering": ordering(q, e),
                    **{f"qualifier_{k}": v for k, v in q.items()},
                    **{f"exception_{k}": v for k, v in e.items()},
                }
            )
    return pd.DataFrame(rows)


def planned_coverage(run: dict, design: dict) -> pd.DataFrame:
    rows = []
    for chain in design["chains"]:
        gens = [g for g in run["generations"] if g["chain_id"] == chain["chain_id"]]
        rows.append(
            {
                **{k: chain[k] for k in ("chain_id", "passage_id", "style", "variant")},
                "generated": len(gens),
                "planned": run["manifest"]["generations"],
                "complete": len(gens) == run["manifest"]["generations"],
            }
        )
    return pd.DataFrame(rows)
