"""Build the local Silver layer: bronze SFS JSON -> provisions.jsonl.

Pure Python. No Spark, no lakehouse-engine, no cluster. This is the local
equivalent of `products/allegoria/silver/silver_sfs.py`, and against the frozen
v1 snapshot it must produce the same rows: 1,952 provisions from 50 documents.

    python scripts/build_silver.py              # v1, the frozen 50-law corpus
    python scripts/build_silver.py --pool v2    # the larger selection pool
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Pool:
    """A corpus to build Silver from.

    v1 carries hard expected counts and keeps them: it is the regression
    corpus, and the assertions are not relaxed to accommodate a bigger pool.
    v2 has no fixed counts because it grows whenever the pool is re-fetched.
    """

    name: str
    bronze_dir: Path
    output_path: Path
    expected_documents: int | None
    expected_provisions: int | None
    # v1 is hand-checked: every one of its 50 documents parses, so a parser
    # failure there is a regression and must stop the build. v2 is whatever
    # Riksdagen returns for 500 arbitrary laws -- some carry no paragraph
    # anchors at all -- and one of those must not abort the pool.
    strict: bool


POOLS = {
    "v1": Pool("v1", BRONZE_DIR, OUTPUT_PATH, EXPECTED_DOCUMENTS, EXPECTED_PROVISIONS, strict=True),
    "v2": Pool(
        "v2",
        PROJECT_ROOT / "data" / "local" / "pool_v2" / "bronze",
        PROJECT_ROOT / "data" / "local" / "provisions_v2.jsonl",
        None,
        None,
        strict=False,
    ),
}

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


def build_provisions(
    bronze_dir: Path, strict: bool = True
) -> tuple[list[dict[str, object]], list[str]]:
    """Parse every bronze document into Silver rows, without writing anything.

    Returns the rows and the ids of documents the parser could not read. In
    strict mode that list is always empty, because the first failure raises.
    """
    bronze_files = sorted(bronze_dir.glob("*.json"))
    if not bronze_files:
        raise SystemExit(f"No bronze documents found in {bronze_dir}")

    provisions: list[dict[str, object]] = []
    unparsable: list[str] = []
    for bronze_file in bronze_files:
        document = json.loads(bronze_file.read_text(encoding="utf-8"))
        document_id = str(document["document_id"])
        try:
            records = parse_sfs_html(str(document["html"]), document_id)
        except ValueError:
            if strict:
                raise
            unparsable.append(document_id)
            continue
        provisions.extend(_silver_row(record, document) for record in records)
    return provisions, unparsable


def build(
    bronze_dir: Path, output_path: Path, pool: Pool = POOLS["v1"]
) -> tuple[list[dict[str, object]], list[str]]:
    provisions, unparsable = build_provisions(bronze_dir, strict=pool.strict)
    _verify(provisions, pool)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for provision in provisions:
            handle.write(json.dumps(provision, ensure_ascii=False) + "\n")

    return provisions, unparsable


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


def _verify(provisions: list[dict[str, object]], pool: Pool = POOLS["v1"]) -> None:
    problems: list[str] = []

    document_count = len({str(provision["document_id"]) for provision in provisions})
    if pool.expected_documents is not None and document_count != pool.expected_documents:
        problems.append(f"documents: expected {pool.expected_documents}, got {document_count}")
    if pool.expected_provisions is not None and len(provisions) != pool.expected_provisions:
        problems.append(f"provisions: expected {pool.expected_provisions}, got {len(provisions)}")

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
    parser.add_argument("--pool", choices=sorted(POOLS), default="v1")
    parser.add_argument("--bronze-dir", type=Path, help="override the pool's bronze directory")
    parser.add_argument("--output", type=Path, help="override the pool's output path")
    args = parser.parse_args()

    pool = POOLS[args.pool]
    bronze_dir = args.bronze_dir or pool.bronze_dir
    output_path = args.output or pool.output_path
    provisions, unparsable = build(bronze_dir, output_path, pool)

    kinds: dict[str, int] = {}
    for provision in provisions:
        kind = str(provision["kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    kind_summary = ", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items()))
    documents = len({str(provision["document_id"]) for provision in provisions})

    skipped = f", {len(unparsable)} unparsable skipped" if unparsable else ""
    print(
        f"SILVER {pool.name} | {documents} documents{skipped} -> {len(provisions)} provisions "
        f"({kind_summary}) | output: {output_path}"
    )


if __name__ == "__main__":
    main()
