"""Build the local Silver layer: bronze SFS JSON -> provisions.jsonl.

Pure Python. No Spark, no lakehouse-engine, no cluster. This is the local
equivalent of `products/allegoria/silver/silver_sfs.py`, and it must produce the
same rows: 1,952 provisions from 50 documents.

    python scripts/build_silver.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from products.allegoria.sfs_parser import parse_sfs_html

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "sfs"
OUTPUT_PATH = PROJECT_ROOT / "data" / "local" / "provisions.jsonl"

# Verified locally 2026-09-10 against the Spark pipeline's output. A mismatch is
# a bug in the parser, the bronze snapshot or this script -- never a new normal.
EXPECTED_DOCUMENTS = 50
EXPECTED_PROVISIONS = 1952

# Copied verbatim from the bronze document onto every provision it yields, so a
# provision carries its own lineage without a join.
DOCUMENT_FIELDS = (
    "document_snapshot_id",
    "title",
    "version",
    "source_page_url",
    "source_sha256",
    "retrieved_at",
)


def build(bronze_dir: Path, output_path: Path) -> list[dict[str, object]]:
    bronze_files = sorted(bronze_dir.glob("*.json"))
    if not bronze_files:
        raise SystemExit(f"No bronze documents found in {bronze_dir}")

    provisions: list[dict[str, object]] = []
    for bronze_file in bronze_files:
        document = json.loads(bronze_file.read_text(encoding="utf-8"))
        document_id = str(document["document_id"])
        for record in parse_sfs_html(str(document["html"]), document_id):
            provisions.append(_silver_row(record, document))

    _verify(provisions, len(bronze_files))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for provision in provisions:
            handle.write(json.dumps(provision, ensure_ascii=False) + "\n")

    return provisions


def _silver_row(record: dict[str, object], document: dict[str, object]) -> dict[str, object]:
    document_id = str(record["document_id"])
    source_anchor = str(record["source_anchor"])
    source_page_url = str(document.get("source_page_url", ""))
    row: dict[str, object] = {
        "provision_id": f"{document_id}:{record['provision_suffix']}",
        **record,
        "document_title": document.get("title", ""),
        "document_version": document.get("version", ""),
        "source_url": f"{source_page_url}#{source_anchor}" if source_page_url else "",
    }
    row.update({field: document.get(field, "") for field in DOCUMENT_FIELDS})
    return row


def _verify(provisions: list[dict[str, object]], document_count: int) -> None:
    problems: list[str] = []

    if document_count != EXPECTED_DOCUMENTS:
        problems.append(f"documents: expected {EXPECTED_DOCUMENTS}, got {document_count}")
    if len(provisions) != EXPECTED_PROVISIONS:
        problems.append(f"provisions: expected {EXPECTED_PROVISIONS}, got {len(provisions)}")

    counts = Counter(str(provision["provision_id"]) for provision in provisions)
    duplicates = sorted(pid for pid, count in counts.items() if count > 1)
    if duplicates:
        problems.append(f"duplicate provision_id: {duplicates[:5]} ({len(duplicates)} total)")

    without_lineage = sum(1 for provision in provisions if not provision["source_sha256"])
    if without_lineage:
        problems.append(f"{without_lineage} provisions without source_sha256")

    if problems:
        raise SystemExit("Silver build failed:\n  " + "\n  ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bronze-dir", type=Path, default=BRONZE_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    provisions = build(args.bronze_dir, args.output)

    kinds: dict[str, int] = {}
    for provision in provisions:
        kind = str(provision["kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    kind_summary = ", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items()))

    print(
        f"SILVER | {EXPECTED_DOCUMENTS} documents -> {len(provisions)} provisions "
        f"({kind_summary}) | output: {args.output}"
    )


if __name__ == "__main__":
    main()
