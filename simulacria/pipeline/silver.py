"""SILVER. Corpus pools, the parse from bronze, and the count contract.

Bronze envelopes in, one verified row per provision out. Not measurement and not
a heuristic: nothing here interprets a provision, it only parses one. Selection
scores these rows; the experiment reads its passages through a domain adapter.

The v1 counts are a contract, not a log line. 50 documents and 1,952 provisions
were verified against the Spark pipeline's output, and `verify` exits non-zero
on any mismatch, together with `provision_id` uniqueness and `source_sha256`
presence. A mismatch means the parser, the data or the environment is wrong --
never that the number moved.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from products.allegoria.sfs_parser import parse_sfs_html

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOCAL_DIR = DATA_DIR / "local"

BRONZE_DIR = DATA_DIR / "bronze" / "sfs"
SOURCE_DIR = DATA_DIR / "source" / "sfs"
OUTPUT_PATH = LOCAL_DIR / "provisions.jsonl"

# Verified locally 2026-09-10 against the Spark pipeline's output. A mismatch is
# a bug in the parser, the bronze snapshot or this code -- never a new normal.
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
    tables_dir: Path


POOLS = {
    "v1": Pool(
        "v1",
        BRONZE_DIR,
        OUTPUT_PATH,
        EXPECTED_DOCUMENTS,
        EXPECTED_PROVISIONS,
        strict=True,
        tables_dir=LOCAL_DIR / "tables",
    ),
    "v2": Pool(
        "v2",
        LOCAL_DIR / "pool_v2" / "bronze",
        LOCAL_DIR / "provisions_v2.jsonl",
        None,
        None,
        strict=False,
        tables_dir=LOCAL_DIR / "tables_v2",
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


def bronze_document(document_id: str, pool: Pool = POOLS["v1"]) -> dict[str, object]:
    """One bronze record, as committed. Used for provenance inspection."""
    path = pool.bronze_dir / f"{document_id}.json"
    if not path.is_file():
        raise SystemExit(f"{document_id} not found in {pool.bronze_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


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
        provisions.extend(silver_row(record, document) for record in records)
    return provisions, unparsable


def build(
    bronze_dir: Path, output_path: Path, pool: Pool = POOLS["v1"]
) -> tuple[list[dict[str, object]], list[str]]:
    """Parse, verify against the pool's contract, then write the JSONL."""
    provisions, unparsable = build_provisions(bronze_dir, strict=pool.strict)
    verify(provisions, pool)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for provision in provisions:
            handle.write(json.dumps(provision, ensure_ascii=False) + "\n")

    return provisions, unparsable


def silver_row(record: dict[str, object], document: dict[str, object]) -> dict[str, object]:
    """One parsed provision plus the lineage it carries without a join."""
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


def check(provisions: list[dict[str, object]], pool: Pool = POOLS["v1"]) -> list[str]:
    """Every way this build violates its pool's contract. Empty means clean."""
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

    return problems


def verify(provisions: list[dict[str, object]], pool: Pool = POOLS["v1"]) -> None:
    """Raise unless the build satisfies its pool's contract."""
    problems = check(provisions, pool)
    if problems:
        raise SystemExit("Silver build failed:\n  " + "\n  ".join(problems))


def load_provisions(path: Path) -> list[dict[str, object]]:
    """Read a built provisions.jsonl."""
    if not path.is_file():
        raise SystemExit(f"{path} not found. Run scripts/pipeline/build_silver.py first.")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_pool(pool: Pool) -> list[dict[str, object]]:
    """Read the provisions a pool has already built."""
    return load_provisions(pool.output_path)
