"""Normative drift across real version chains: how a norm's requirement posture
changes over decades. LLM-free, deterministic, real data.

For four IETF protocol families, each with several dated revisions of the same
spec, the deterministic RFC 2119 reader profiles every version's requirement
strength (MUST=binding, SHOULD=weak, MAY=absent). The output is a time series --
the binding share per version -- and the signed posture delta between consecutive
versions (a falling MUST share is a looser posture). This is the founding
question ("does normative drift have a sign?") answered on real institutional
drift, at scale, with graphs.

Only revisions that use the uppercase RFC 2119 convention (1997+) are comparable;
earlier specs (e.g. TLS 1.0 / RFC 2246) are excluded and noted.

    python scripts/investigations/normative_drift.py

No model, no network (reads the RFC text committed under data/source/rfc/).
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from meaningquality.rfc import profile, requirements

ROOT = Path(__file__).resolve().parents[2]

# (protocol family, rfc number, year, short title). Real IETF obsoletes chains.
CHAINS = {
    "TLS": [("4346", 2006, "TLS 1.1"), ("5246", 2008, "TLS 1.2"), ("8446", 2018, "TLS 1.3")],
    "HTTP": [
        ("2616", 1999, "HTTP/1.1"),
        ("7230", 2014, "HTTP/1.1 syntax/routing"),
        ("9110", 2022, "HTTP semantics"),
    ],
    "SMTP": [("2821", 2001, "SMTP"), ("5321", 2008, "SMTP")],
    "Cookies": [("2965", 2000, "Cookie2"), ("6265", 2011, "Cookies")],
}


def _profile(number: str) -> dict | None:
    path = ROOT / f"data/source/rfc/rfc-{number}.txt"
    if not path.exists():
        return None
    return profile(requirements(path.read_text(encoding="utf-8")))


def build() -> dict:
    protocols = []
    for family, versions in CHAINS.items():
        rows = []
        for number, year, title in versions:
            prof = _profile(number)
            if prof and prof["requirements"]:
                rows.append({"rfc": f"rfc-{number}", "year": year, "title": title, **prof})
        deltas = []
        for before, after in zip(rows, rows[1:]):
            delta = round(after["shares_pct"]["binding"] - before["shares_pct"]["binding"], 1)
            deltas.append(
                {
                    "from": before["rfc"],
                    "to": after["rfc"],
                    "binding_share_delta_pp": delta,
                    "posture": "looser" if delta < 0 else "stricter" if delta > 0 else "flat",
                }
            )
        protocols.append({"protocol": family, "versions": rows, "deltas": deltas})
    return {
        "source": "IETF RFCs (rfc-editor.org), committed under data/source/rfc/",
        "method": "deterministic RFC 2119 reader; requirement strength MUST=binding, SHOULD=weak, "
        "MAY=absent; binding share per version is the posture; falling share = looser. No model.",
        "note": "Only uppercase-RFC2119 revisions (1997+) are comparable; TLS 1.0 (RFC 2246) excluded.",
        "protocols": protocols,
    }


def write(report: dict) -> tuple[Path, Path]:
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "normative_drift.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = out_dir / "normative_drift.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(
            [
                "protocol",
                "rfc",
                "year",
                "title",
                "requirements",
                "must_pct",
                "should_pct",
                "may_pct",
            ]
        )
        for p in report["protocols"]:
            for v in p["versions"]:
                s = v["shares_pct"]
                w.writerow(
                    [
                        p["protocol"],
                        v["rfc"],
                        v["year"],
                        v["title"],
                        v["requirements"],
                        s["binding"],
                        s["weak"],
                        s["absent"],
                    ]
                )
    return json_path, csv_path


def main() -> None:
    report = build()
    json_path, csv_path = write(report)
    for p in report["protocols"]:
        print(f"\n{p['protocol']}")
        for v in p["versions"]:
            s = v["shares_pct"]
            print(
                f"  {v['year']} {v['rfc']:<9} {v['requirements']:>3} reqs  "
                f"MUST {s['binding']:>4}%  SHOULD {s['weak']:>4}%  MAY {s['absent']:>4}%"
            )
        for d in p["deltas"]:
            print(
                f"    {d['from']} -> {d['to']}: MUST-share {d['binding_share_delta_pp']:+} pp ({d['posture']})"
            )
    print(f"\nWrote {json_path.relative_to(ROOT)} and {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
