"""Real signed protocol drift between two versions of a spec.

Runs on the committed RFC plain text (RFC 2965, the 2000 cookie spec, and its
2011 successor RFC 6265, which obsoletes it). Reports two honest layers:

- per-requirement drift: requirements matched across versions whose RFC 2119
  keyword changed strength, signed by the engine (MUST->SHOULD = loosening).
  For a full rewrite this is expectedly near zero -- sentences do not survive
  verbatim -- and that is reported truthfully, not padded.
- profile shift: the corpus-level requirement-strength profile of each version.
  A smaller binding (MUST) share in the successor is an overall loosening of the
  spec's posture even when no single requirement matches one-to-one.

No model. Fetched from rfc-editor.org into data/source/rfc/ (source pinned there).

    python scripts/investigations/rfc_drift.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from meaningquality.rfc import drift, profile, requirements

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "data/source/rfc/rfc-2965.txt"
NEW = ROOT / "data/source/rfc/rfc-6265.txt"


def build() -> dict:
    old = requirements(OLD.read_text(encoding="utf-8"))
    new = requirements(NEW.read_text(encoding="utf-8"))
    return {
        "source": "IETF RFC 2965 (2000) and RFC 6265 (2011, obsoletes 2965), rfc-editor.org",
        "method": "deterministic RFC 2119 reader; per-requirement drift signed by the engine; "
        "profile shift is a descriptive corpus-level view. No model.",
        "old": {"rfc": OLD.stem, **profile(old)},
        "new": {"rfc": NEW.stem, **profile(new)},
        "matched_requirement_drift": drift(old, new),
    }


def main() -> None:
    report = build()
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "rfc_drift.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for key in ("old", "new"):
        d = report[key]
        print(
            f"{d['rfc']}: {d['requirements']} reqs  MUST {d['shares_pct']['binding']}%  "
            f"SHOULD {d['shares_pct']['weak']}%  MAY {d['shares_pct']['absent']}%"
        )
    print(f"per-requirement signed drifts (matched): {len(report['matched_requirement_drift'])}")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
