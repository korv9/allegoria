"""SELECTION. Everything the pipeline knows about one provision, in one call.

Not measurement. This assembles what the selection heuristics produced; it
decides nothing. Anything here that looks like a judgment -- a marker firing, a
determinacy rung, a rank -- is a heuristic output, and which part a qualifier
attaches to is deliberately absent because that decides the sign.

Exists so the notebook's drill-down cell is one import and one call rather than
a reimplementation of the pipeline in a cell.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from simulacria.selection.determinacy import (
    provision_determinacy,
    qualifier_determinacy,
    qualifier_spans_with_offsets,
)
from simulacria.selection.highlight import marker_spans
from simulacria.selection.markers import ceiling_hits
from simulacria.selection.pools import POOLS, SOURCE_DIR, Pool, bronze_document, load_pool
from simulacria.selection.shortlist import ranked, score_breakdown
from simulacria.selection.tables import connect


def provenance(document_id: str, pool: Pool = POOLS["v1"]) -> dict[str, object]:
    """The chain from committed bytes to bronze record, and whether it holds.

    Recomputes the digest from the file on disk rather than trusting the one
    recorded beside it -- a hash that is only ever read proves nothing.
    """
    bronze = bronze_document(document_id, pool)
    raw_path = SOURCE_DIR / f"{document_id}.xml"
    recorded = str(bronze["source_sha256"])

    computed: str | None = None
    raw_bytes: bytes | None = None
    if raw_path.is_file():
        raw_bytes = raw_path.read_bytes()
        computed = hashlib.sha256(raw_bytes).hexdigest()

    return {
        "document_id": document_id,
        "title": bronze["title"],
        "version": bronze["version"],
        "source_data_url": bronze["source_data_url"],
        "raw_file": raw_path if raw_path.is_file() else None,
        "raw_bytes": len(raw_bytes) if raw_bytes is not None else None,
        "recorded_sha256": recorded,
        "computed_sha256": computed,
        "sha256_matches": computed == recorded if computed else None,
        "roundtrips_to_bronze": (
            str(bronze["raw_xml"]).encode("utf-8") == raw_bytes if raw_bytes is not None else None
        ),
        "document_snapshot_id": bronze["document_snapshot_id"],
        "retrieved_at": bronze["retrieved_at"],
        "bronze_keys": sorted(bronze),
    }


def tables_containing(provision_id: str, tables_dir: Path) -> dict[str, int]:
    """Row counts for this provision in each Parquet table."""
    connection = connect(tables_dir)
    try:
        return {
            name: connection.execute(
                f'select count(*) from "{name}" where provision_id = ?', [provision_id]
            ).fetchone()[0]
            for name in ("provisions", "candidates", "marker_hits")
        }
    finally:
        connection.close()


def inspect_provision(
    provision_id: str,
    pool: Pool = POOLS["v1"],
    provisions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Text, markers, determinacy, score, rank and table membership.

    Pass `provisions` to avoid re-reading the pool when inspecting several.
    """
    rows = provisions if provisions is not None else load_pool(pool)
    match = next((row for row in rows if str(row["provision_id"]) == provision_id), None)
    if match is None:
        raise SystemExit(f"{provision_id} not found in pool {pool.name}")

    text = str(match["text"])
    candidates = ranked(rows)
    candidate = candidates.get(provision_id)

    state, specific, vague = provision_determinacy(text)
    q_state, q_specific, q_vague = qualifier_determinacy(text)

    return {
        "provision": match,
        "text": text,
        "is_candidate": candidate is not None,
        "rank": candidate["rank"] if candidate else None,
        "score": candidate["score"] if candidate else None,
        "score_breakdown": score_breakdown(text),
        "marker_spans": marker_spans(text),
        "qualifier_spans": qualifier_spans_with_offsets(text),
        "provision_determinacy": {"state": state, "specific": specific, "vague": vague},
        "qualifier_determinacy": {"state": q_state, "specific": q_specific, "vague": q_vague},
        "ceiling_flags": [window for window, bounded in ceiling_hits(text) if bounded],
        "tables": tables_containing(provision_id, pool.tables_dir),
        "pool": pool.name,
    }
