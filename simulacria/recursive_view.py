"""Displays for actual recursive run evidence."""

import json
from html import escape

import matplotlib.pyplot as plt
import pandas as pd


def error_summary(run, directory):
    rows = []
    for event in run["calls"]:
        if event["event"] != "received" or event["http_status"] == 200:
            continue
        # Anthropic errors are {"type": "error", "error": {"type": ..., ...}}. A
        # gateway can instead return an HTML page, which must not crash a report.
        try:
            error = json.loads((directory / event["raw_path"]).read_text(encoding="utf-8"))
            error = error.get("error", {}) if isinstance(error, dict) else {}
        except ValueError:
            error = {}
        reason = error.get("type", "http_error") if isinstance(error, dict) else "http_error"
        rows.append({"HTTP": event["http_status"], "Orsak": reason})
    if not rows:
        return pd.DataFrame(columns=["HTTP", "Orsak", "Antal"])
    return pd.DataFrame(rows).value_counts().rename("Antal").reset_index()


def chain_cards(run, observations):
    sources = {s["passage_id"]: s for s in run["sources"]}
    groups = {}
    for row in run["generations"]:
        groups.setdefault(row["chain_id"], []).append(row)
    cards = []
    for chain, generations in sorted(groups.items()):
        source = sources[generations[0]["passage_id"]]
        panels = []
        for row in [source] + sorted(generations, key=lambda g: g["generation"]):
            readings = observations[observations.text_id == row["text_id"]][
                ["slot_id", "status", "quote", "note"]
            ]
            panels.append(
                f'<section style="padding:12px;border-top:1px solid #ddd"><h4>Generation {row["generation"]}</h4>'
                f'<p style="white-space:pre-wrap;line-height:1.6">{escape(row["text"])}</p>'
                + readings.to_html(index=False, escape=True)
                + "</section>"
            )
        cards.append(
            '<details style="margin:12px 0;border:1px solid #bbb;padding:12px">'
            f"<summary><b>{escape(chain)}</b> · {len(generations)} generations</summary>"
            f"<p>Source: {escape(source['source_url'])}</p>" + "".join(panels) + "</details>"
        )
    return "".join(cards) or "<p>No generated texts exist.</p>"


def law_curves(frame):
    law = frame[frame.norm_group == "statutory"].copy()
    law["slot_category"] = [
        "Exception"
        if k == "exception"
        else "Condition on exception"
        if a == "exception"
        else "Other slots"
        for k, a in zip(law.kind, law.attaches_to)
    ]
    counts = law.groupby(["generation", "slot_category", "status"]).size().unstack(fill_value=0)
    for status in ("present", "absent", "uncertain", "not_read"):
        if status not in counts:
            counts[status] = 0
    counts["available"] = counts.present + counts.absent + counts.uncertain
    counts["present_fraction"] = counts.present / counts.available.replace(0, float("nan"))
    fig, ax = plt.subplots(figsize=(10, 4))
    for category, subset in counts.reset_index().groupby("slot_category"):
        series = subset.set_index("generation").present_fraction.reindex(range(11))
        ax.plot(series.index, series.values, marker="o", label=category)
    ax.set(
        xlabel="Generation",
        ylabel="Share present among read slots",
        ylim=(-0.05, 1.05),
        xticks=range(11),
        title="Model observations - gaps are not filled in",
    )
    ax.legend()
    plt.tight_layout()
    plt.show()
    return counts.reset_index()
