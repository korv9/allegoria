"""Measure how often debate speech makes a checkable deontic claim about a rule.

The debate-vs-law application only has something to measure where a speech
actually characterises what a rule requires. This screens the real Riksdagen
corpus (the partiledardebatt-analys portfolio-data) for that, and contrasts
party-leader debate with issue (sakdebatt) debate.

    python scripts/investigations/debate_eligibility.py /path/to/portfolio-data

It is a keyword screen -- an upper bound on eligibility, not a hand count -- and
the numbers it writes name the source and the method so the claim is auditable.
No model, no network; reads only committed JSON.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# "a law / rule / proposal ... <modal>" within a short window: the same screen
# that returned 0/933 on party-leader excerpts.
CLAIM = re.compile(
    r"(lag(en|stiftning|arna)?|regel|regler|regelverk|förslag(et)?|propositionen|kravet)\b"
    r"[^.]{0,60}\b(ska|måste|får|kräver|förbjud|tillåt|innebär|tvingar|slopa|ta bort|inför)",
    re.I,
)
LAS = re.compile(
    r"anställningsskydd|turordning|saklig grund|provanställ|uppsägningstid|\bLAS\b", re.I
)


def scan_texts(texts: list[str]) -> dict:
    hits = sum(1 for t in texts if CLAIM.search(t))
    total = len(texts)
    return {
        "speeches": total,
        "deontic_claims": hits,
        "share_pct": round(100 * hits / total, 1) if total else 0.0,
    }


def party_leader(pdata: Path) -> dict:
    texts = []
    for path in sorted(pdata.glob("sessions/*/decision-speech-links.json")):
        rows = json.loads(path.read_text(encoding="utf-8")).get("data", [])
        texts += [r.get("speech_excerpt", "") for r in rows]
    return scan_texts(texts)


def issues(pdata: Path) -> dict:
    texts, las_debates = [], set()
    for path in glob.glob(str(pdata / "issues/*/*.json")):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = data["data"] if isinstance(data, dict) and "data" in data else data
        if not isinstance(rows, list):
            continue
        for sp in rows:
            if not isinstance(sp, dict):
                continue
            text = sp.get("speech_text", "")
            texts.append(text)
            if LAS.search(text):
                las_debates.add(sp.get("debate_title", ""))
    out = scan_texts(texts)
    out["las_debates"] = len(las_debates)
    return out


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: debate_eligibility.py /path/to/portfolio-data")
    pdata = Path(sys.argv[1])
    report = {
        "source": "Sveriges riksdag via partiledardebatt-analys portfolio-data",
        "method": "keyword screen for 'law/rule/proposal + modal'; upper bound, not a hand count",
        "party_leader_debate": party_leader(pdata),
        "issue_debate": issues(pdata),
    }
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "debate_eligibility.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pl, iss = report["party_leader_debate"], report["issue_debate"]
    print(f"party-leader: {pl['deontic_claims']}/{pl['speeches']} = {pl['share_pct']}%")
    print(
        f"issue debate: {iss['deontic_claims']}/{iss['speeches']} = {iss['share_pct']}% "
        f"({iss['las_debates']} LAS-touching debates)"
    )
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
