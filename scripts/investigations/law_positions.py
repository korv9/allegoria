"""Join, per decision (betänkande): the law it concerns, each party's argued
DIRECTION (skärpa/luckra) and each party's actual VOTE, with sources.

Three real layers from the partiledardebatt-analys export, joined for the sessions
where votes exist (2024/25, 2025/26):

  votes  (sessions/<s>/votes.json)          party position per decision point
  laws   (sessions/<s>/decision-motions.json) the motions/propositions decided
  debate (issues/*/*.json)                   the sakdebatt, screened for direction

Votes are real and clean. Direction is a LEXICAL screen (verbatim kept for every
hit). The join is exact decision-title match between a debate and a vote. A vote
on a committee point is not automatically support for a single motion -- see the
source repo's own caveat.

    python scripts/investigations/law_positions.py /path/to/portfolio-data

No model, no network.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ("2024-25", "2025-26")
PARTIES = ("S", "M", "SD", "C", "V", "KD", "L", "MP")

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


def norm(title: str) -> str:
    return " ".join(title.split()).strip().lower()


def sentence(text: str, start: int) -> str:
    lo = text.rfind(".", 0, start) + 1
    hi = text.find(".", start)
    hi = hi + 1 if hi != -1 else min(len(text), start + 150)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()[:170]


def load_votes(pdata: Path) -> dict:
    """(session, designation, title) -> {party -> {position, dist, url, points}}."""
    out: dict = defaultdict(
        lambda: defaultdict(lambda: {"dist": Counter(), "url": "", "points": set()})
    )
    for s in SESSIONS:
        p = pdata / f"sessions/{s}/votes.json"
        if not p.exists():
            continue
        for r in json.loads(p.read_text(encoding="utf-8")).get("data", []):
            party = r.get("party", "")
            if party not in PARTIES:
                continue
            key = (r["session"], r["designation"], norm(r["title"]))
            cell = out[key][party]
            cell["dist"][r.get("party_position", "?")] += 1
            cell["url"] = r.get("source_url", "")
            cell["points"].add(r.get("point"))
            out[key]["_title"] = r["title"]
    return out


def load_motions(pdata: Path) -> dict:
    """designation -> list of proposition/motion references (the concrete law)."""
    by_vote: dict = defaultdict(list)
    for s in SESSIONS:
        vp = pdata / f"sessions/{s}/votes.json"
        mp = pdata / f"sessions/{s}/decision-motions.json"
        if not (vp.exists() and mp.exists()):
            continue
        vote_to_desig = {
            r["vote_id"]: r["designation"]
            for r in json.loads(vp.read_text(encoding="utf-8"))["data"]
        }
        for m in json.loads(mp.read_text(encoding="utf-8")).get("data", []):
            desig = vote_to_desig.get(m["vote_id"])
            if desig:
                by_vote[desig].append(
                    {
                        "ref": m.get("motion_reference", ""),
                        "title": m.get("motion_title", ""),
                        "url": m.get("motion_url", ""),
                    }
                )
    props: dict = {}
    for desig, ms in by_vote.items():
        seen, refs = set(), []
        for m in ms:
            pm = re.search(r"prop\.?\s*\d{4}/\d{2}:\d+", m["title"])
            label = pm.group(0) if pm else m["ref"]
            if label and label not in seen:
                seen.add(label)
                refs.append({"label": label, "url": m["url"]})
        props[desig] = refs[:6]
    return props


def load_debate_direction(pdata: Path) -> dict:
    """norm(title) -> {party -> {t, l, ex_t, ex_l}} from the sakdebatt."""
    out: dict = defaultdict(
        lambda: defaultdict(lambda: {"t": 0, "l": 0, "ex_t": None, "ex_l": None})
    )
    for s in SESSIONS:
        for f in glob.glob(str(pdata / f"issues/{s}/*.json")):
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            speeches = data.get("data", data) if isinstance(data, dict) else data
            for sp in speeches if isinstance(speeches, list) else []:
                if not isinstance(sp, dict) or sp.get("party") not in PARTIES:
                    continue
                title, party, text = (
                    norm(sp.get("debate_title", "")),
                    sp["party"],
                    sp.get("speech_text", ""),
                )
                cell = out[title][party]
                for direction, pat, key in (("t", TIGHTEN, "ex_t"), ("l", LOOSEN, "ex_l")):
                    m = pat.search(text)
                    if m:
                        cell[direction] += 1
                        if cell[key] is None:
                            cell[key] = {
                                "s": sentence(text, m.start()),
                                "w": sp.get("speaker", ""),
                                "u": sp.get("source_url", ""),
                            }
    return out


def build(pdata: Path) -> dict:
    votes, motions, direction = load_votes(pdata), load_motions(pdata), load_debate_direction(pdata)
    decisions = []
    for (session, desig, ntitle), cells in votes.items():
        title = cells.pop("_title", desig)
        dir_by_party = direction.get(ntitle, {})
        parties = {}
        for party in PARTIES:
            v = cells.get(party)
            d = dir_by_party.get(party)
            if not v and not d:
                continue
            pos = v["dist"].most_common(1)[0][0] if v else None
            parties[party] = {
                "vote": pos,
                "vote_dist": dict(v["dist"]) if v else {},
                "vote_url": v["url"] if v else "",
                "tighten": d["t"] if d else 0,
                "loosen": d["l"] if d else 0,
                "ex_t": d["ex_t"] if d else None,
                "ex_l": d["ex_l"] if d else None,
            }
        has_debate = ntitle in direction
        decisions.append(
            {
                "session": session,
                "designation": desig,
                "title": title,
                "laws": motions.get(desig, []),
                "has_debate": has_debate,
                "parties": parties,
            }
        )
    decisions.sort(key=lambda x: (not x["has_debate"], x["designation"]))
    return {
        "source": "Sveriges riksdag via partiledardebatt-analys @14c58f2 (votes, decision-motions, issues)",
        "method": "votes are real per-point party positions (modal shown); direction is a lexical screen "
        "of the sakdebatt with verbatim kept; join is exact decision-title match. A point vote is not "
        "automatic support for one motion.",
        "sessions": list(SESSIONS),
        "decisions_with_debate": sum(d["has_debate"] for d in decisions),
        "decisions_total": len(decisions),
        "decisions": decisions,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: law_positions.py /path/to/portfolio-data")
    report = build(Path(sys.argv[1]))
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "law_positions.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"decisions: {report['decisions_total']} ({report['decisions_with_debate']} with a matched debate)"
    )
    print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
