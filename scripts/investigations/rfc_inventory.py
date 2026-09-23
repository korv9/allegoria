"""Cross-domain demonstration: read a real IETF RFC's requirements with the same
engine, no model, no network.

Runs the deterministic RFC 2119 reader over the RFC plain text committed under
data/source/rfc/ and writes an inventory -- every MUST/SHOULD/MAY requirement,
its modality rung, and the counts -- to review/. This is a real reading of a real
technical norm, proving the meaning-quality engine is not tied to Swedish statute.
Signed drift falls out of `meaningquality.rfc.drift` as soon as a second version
of the same RFC is available (an obsoletes/updated-by successor).

    python scripts/investigations/rfc_inventory.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from meaningquality.rfc import requirements

ROOT = Path(__file__).resolve().parents[2]
RFCS = ["data/source/rfc/rfc-6265.txt", "data/source/rfc/rfc-2119.txt"]


def build() -> dict:
    docs = []
    for rel in RFCS:
        path = ROOT / rel
        if not path.exists():
            continue
        reqs = requirements(path.read_text(encoding="utf-8"))
        by_keyword = Counter(r.keyword for r in reqs)
        by_modality = Counter(r.modality.name.lower() for r in reqs)
        docs.append(
            {
                "rfc": path.stem,
                "source": rel,
                "requirements": len(reqs),
                "by_keyword": dict(by_keyword.most_common()),
                "by_modality": dict(by_modality),
                "examples": [
                    {
                        "keyword": r.keyword,
                        "modality": r.modality.name.lower(),
                        "text": r.sentence[:180],
                    }
                    for r in reqs[:8]
                ],
            }
        )
    return {
        "source": "IETF RFC plain text committed under data/source/rfc/",
        "method": "deterministic RFC 2119 reader; MUST/SHALL=binding, SHOULD/RECOMMENDED=weak, "
        "MAY/OPTIONAL=absent; no model, no network. Signed drift needs a second version.",
        "documents": docs,
    }


def main() -> None:
    report = build()
    out_dir = ROOT / "review" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "rfc_requirements.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for d in report["documents"]:
        print(f"{d['rfc']}: {d['requirements']} requirements  {d['by_modality']}")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
