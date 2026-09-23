"""Screen every issue debate for a proposed regulatory DIRECTION, per party.

This is Läge B at scale. It is NOT the validated deterministic direction metric
(which needs hand-annotated slots per provision). It is a lexical screen: it looks
for phrases that argue for MORE regulatory constraint (skärpa/reglera/förbjuda,
"tightening") or LESS (slopa/avreglera/luckra, "loosening") inside a debate whose
title names the issue/law, and tags the speaker's party. It has false positives,
so every hit keeps its verbatim sentence and source link for human verification.

Direction here means scope of permitted action for the regulated actor: more
constraint / stronger protection duty = tightening; less = loosening. It is not a
judgement of good or bad.

    python scripts/investigations/proposal_scan.py /path/to/portfolio-data

No model, no network; reads committed issue JSON only.
"""

from __future__ import annotations

import csv
import glob
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TIGHTEN = re.compile(
    r"\b(skärp\w*|hårdare|strängare|förbjud\w*|förbud mot|återinför\w*|kriminalisera\w*|"
    r"höja kraven|inför(a|as)? (ett )?krav|ställa (högre |hårdare )?krav|"
    r"stärka (skyddet|rätten|anställningsskyddet)|utöka skyddet|skärpta krav)\b",
    re.I,
)
LOOSEN = re.compile(
    r"\b(slopa\w*|avskaffa\w*|avreglera\w*|luckra upp|mjuka upp|ta bort (undantag\w*|regler\w*|"
    r"kravet|förbudet|regleringen)|fler undantag|utöka undantag\w*|förenkla regel\w*|"
    r"sänka kraven|minska regelbördan|göra det (lättare|enklare) att|liberalisera\w*|"
    r"avskaffa förbud\w*)\b",
    re.I,
)
PARTY = {"FP": "L", "KDS": "KD"}  # documented harmonisation in the source repo


def sentence(text: str, start: int) -> str:
    lo = text.rfind(".", 0, start) + 1
    hi = text.find(".", start)
    hi = hi + 1 if hi != -1 else min(len(text), start + 160)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def scan(pdata: Path) -> list[dict]:
    rows = []
    for f in glob.glob(str(pdata / "issues/*/*.json")):
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        speeches = data["data"] if isinstance(data, dict) and "data" in data else data
        if not isinstance(speeches, list):
            continue
        for sp in speeches:
            if not isinstance(sp, dict):
                continue
            party = PARTY.get((sp.get("party") or "").upper(), (sp.get("party") or "").upper())
            if party in ("", "-", "TALMANNEN"):
                continue
            text = sp.get("speech_text", "")
            for direction, pat in (("tightening", TIGHTEN), ("loosening", LOOSEN)):
                m = pat.search(text)
                if m:
                    rows.append(
                        {
                            "party": party,
                            "issue": sp.get("debate_title", ""),
                            "session": sp.get("session", ""),
                            "direction": direction,
                            "cue": m.group(0).lower(),
                            "sentence": sentence(text, m.start()),
                            "speaker": sp.get("speaker", ""),
                            "source_url": sp.get("source_url", ""),
                        }
                    )
    return rows


def party_summary(rows: list[dict]) -> list[dict]:
    agg: dict[str, dict] = defaultdict(lambda: {"tightening": set(), "loosening": set()})
    for r in rows:
        agg[r["party"]][r["direction"]].add((r["issue"], r["session"]))
    out = []
    for party, d in agg.items():
        t, loose = len(d["tightening"]), len(d["loosening"])
        total = t + loose
        out.append(
            {
                "party": party,
                "tighten_debates": t,
                "loosen_debates": loose,
                "net": t - loose,
                # loosen share removes the baseline that "skärpa" is simply a more
                # common political word than "slopa"; the raw totals are frequency
                # biased and should not be read as a party's overall stance.
                "loosen_share_pct": round(100 * loose / total, 1) if total else 0.0,
                "lean": "skärpa" if t > loose else "luckra" if loose > t else "jämnt",
            }
        )
    return sorted(out, key=lambda x: -(x["tighten_debates"] + x["loosen_debates"]))


def by_issue(rows: list[dict], top: int = 40) -> list[dict]:
    agg: dict[str, dict] = defaultdict(
        lambda: defaultdict(lambda: {"tightening": 0, "loosening": 0, "ex": {}})
    )
    for r in rows:
        cell = agg[r["issue"]][r["party"]]
        cell[r["direction"]] += 1
        cell["ex"].setdefault(
            r["direction"],
            {"sentence": r["sentence"], "speaker": r["speaker"], "source_url": r["source_url"]},
        )
    issues = []
    for issue, parties in agg.items():
        total = sum(c["tightening"] + c["loosening"] for c in parties.values())
        issues.append((total, issue, parties))
    issues.sort(reverse=True, key=lambda x: x[0])
    out = []
    for total, issue, parties in issues[:top]:
        out.append(
            {
                "issue": issue,
                "total_hits": total,
                "parties": {
                    p: {
                        "tightening": c["tightening"],
                        "loosening": c["loosening"],
                        "examples": c["ex"],
                    }
                    for p, c in sorted(
                        parties.items(), key=lambda x: -(x[1]["tightening"] + x[1]["loosening"])
                    )
                },
            }
        )
    return out


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: proposal_scan.py /path/to/portfolio-data")
    rows = scan(Path(sys.argv[1]))
    summary = party_summary(rows)
    issues = by_issue(rows)
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "source": "Sveriges riksdag via partiledardebatt-analys portfolio-data (issues/)",
        "method": "LEXICAL directional screen, not the validated deterministic metric; "
        "tightening=more constraint/protection, loosening=less; false positives expected; "
        "every hit keeps its verbatim sentence and source for review",
        "total_hits": len(rows),
        "party_summary": summary,
        "top_issues": issues,
    }
    (out_dir / "proposal_scan.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "proposal_scan_party_summary.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.writer(h)
        w.writerow(["party", "tighten_debates", "loosen_debates", "net", "lean"])
        for r in summary:
            w.writerow([r["party"], r["tighten_debates"], r["loosen_debates"], r["net"], r["lean"]])
    print(f"total hits: {len(rows)}")
    for r in summary:
        print(
            f"  {r['party']:<4} skärpa={r['tighten_debates']:<4} luckra={r['loosen_debates']:<4} lean={r['lean']}"
        )
    print(f"wrote {(out_dir / 'proposal_scan.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
