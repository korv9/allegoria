"""Fetch plain-text RFCs into the bronze layer, bytes first.

    python scripts/pipeline/ingest_rfc.py 2119 8446

Writes `data/source/rfc/rfc-<n>.txt` with the exact bytes the server returned and
`data/bronze/rfc/rfc-<n>.json` with the envelope that pins them: URL, retrieval
time, SHA-256 and the decoded text. Existing files are never overwritten -- a
re-fetch that differs is a new document, not an update of the evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

from simulacria.domains.rfc import BRONZE_DIR, SOURCE_DIR, sections

URL = "https://www.rfc-editor.org/rfc/rfc{number}.txt"


def fetch(number: int, root: Path, timeout: int = 60) -> Path:
    source_path = root / SOURCE_DIR / f"rfc-{number}.txt"
    bronze_path = root / BRONZE_DIR / f"rfc-{number}.json"
    if source_path.exists() or bronze_path.exists():
        raise SystemExit(f"rfc-{number} is already ingested; delete it deliberately to refetch")
    url = URL.format(number=number)
    with urlopen(
        Request(url, headers={"User-Agent": "allegoria-research/1.0"}), timeout=timeout
    ) as answer:
        raw = answer.read()
    text = raw.decode("utf-8")
    found = sections(text)
    if not found:
        raise SystemExit(f"rfc-{number}: no numbered sections were found; check the format")
    title = next((line.strip() for line in text.splitlines() if line.strip()), f"RFC {number}")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    bronze_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(raw)
    bronze_path.write_text(
        json.dumps(
            {
                "document_id": f"rfc-{number}",
                "title": f"RFC {number}",
                "heading_line": title,
                "source_page_url": url,
                "source_sha256": sha256(raw).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "byte_count": len(raw),
                "section_count": len(found),
                "text": text,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"rfc-{number}: {len(raw)} bytes, {len(found)} sections -> {bronze_path}")
    return bronze_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("numbers", type=int, nargs="+", help="RFC numbers, e.g. 2119")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[2]
    for rfc_number in args.numbers:
        fetch(rfc_number, project_root)
