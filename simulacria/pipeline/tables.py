"""GOLD. Build queryable Parquet tables from the local silver layer.

Turns `data/local/provisions.jsonl` and the candidate shortlist into four
Parquet files under `data/local/tables/`, so the shortlist can be interrogated
with SQL instead of read off a terminal.

    python scripts/pipeline/build_tables.py
    python scripts/report/query.py -c "select * from candidates limit 5"

`marker_hits` is built across ALL provisions, not only the surfaced candidates.
That is what makes "which markers never fire" and "duty + exception but no
qualifier" answerable -- a near-miss is by definition not a candidate.

Every `matched_span` is asserted to be a verbatim substring of the provision
text at its recorded offset. PROTOCOL.md requires that discipline of the
extractor; it is cheap to enforce here and keeps the habit in one place.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from simulacria.pipeline.silver import load_provisions
from simulacria.selection.markers import (
    DUTY_MARKERS,
    EXCEPTION_MARKERS,
    MARKER_SETS,
    QUALIFIER_MARKERS,
    iter_matches,
    top_marker,
)
from simulacria.selection.shortlist import shortlist

PROVISION_COLUMNS = (
    ("provision_id", "VARCHAR"),
    ("document_id", "VARCHAR"),
    ("document_title", "VARCHAR"),
    ("document_version", "VARCHAR"),
    ("kind", "VARCHAR"),
    ("chapter", "VARCHAR"),
    ("label", "VARCHAR"),
    ("heading", "VARCHAR"),
    ("order", "INTEGER"),
    ("text", "VARCHAR"),
    ("char_count", "INTEGER"),
    ("source_url", "VARCHAR"),
    ("source_sha256", "VARCHAR"),
)

CANDIDATE_COLUMNS = (
    ("provision_id", "VARCHAR"),
    ("rank", "INTEGER"),
    ("score", "DOUBLE"),
    ("has_duty", "BOOLEAN"),
    ("has_exception", "BOOLEAN"),
    ("has_qualifier", "BOOLEAN"),
    ("determinacy", "VARCHAR"),
    # Provision-level `determinacy` above grades the whole text and still drives
    # the score. This grades the qualifier clause itself, which is what the
    # DIRECTION.md ladder is actually about and what specimens are selected on.
    ("qualifier_determinacy", "VARCHAR"),
    ("duty_marker", "VARCHAR"),
    ("exception_marker", "VARCHAR"),
    ("qualifier_marker", "VARCHAR"),
    ("char_count", "INTEGER"),
)

MARKER_HIT_COLUMNS = (
    ("provision_id", "VARCHAR"),
    ("category", "VARCHAR"),
    ("marker", "VARCHAR"),
    ("matched_span", "VARCHAR"),
    ("char_offset", "INTEGER"),
)

# Not in the original three tables, but "which markers never fire" cannot be
# asked without an inventory: a marker that never matches leaves no hit rows.
# Joining against this beats hardcoding the marker list into every query.
MARKER_COLUMNS = (
    ("category", "VARCHAR"),
    ("marker", "VARCHAR"),
    ("weight", "INTEGER"),
    ("pattern", "VARCHAR"),
)


def provision_rows(provisions: list[dict[str, object]]) -> list[tuple[object, ...]]:
    return [
        (
            str(provision["provision_id"]),
            str(provision["document_id"]),
            str(provision["document_title"]),
            provision["document_version"],
            str(provision["kind"]),
            str(provision["chapter"]),
            str(provision["label"]),
            str(provision["heading"]),
            int(provision["order"]),
            str(provision["text"]),
            len(str(provision["text"])),
            str(provision["source_url"]),
            str(provision["source_sha256"]),
        )
        for provision in provisions
    ]


def candidate_rows(candidates: list[dict[str, object]]) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for rank, candidate in enumerate(candidates, start=1):
        text = str(candidate["text"])
        rows.append(
            (
                str(candidate["provision_id"]),
                rank,
                float(candidate["score"]),
                True,
                True,
                True,
                str(candidate["determinacy"]),
                str(candidate["qualifier_determinacy"]),
                top_marker(text, DUTY_MARKERS),
                top_marker(text, EXCEPTION_MARKERS),
                top_marker(text, QUALIFIER_MARKERS),
                int(candidate["char_count"]),
            )
        )
    return rows


def marker_rows() -> list[tuple[object, ...]]:
    """The marker inventory itself, so never-firing markers stay nameable."""
    return [
        (category, label, weight, pattern.pattern)
        for category, markers in MARKER_SETS
        for label, pattern, weight in markers
    ]


def marker_hit_rows(provisions: list[dict[str, object]]) -> list[tuple[object, ...]]:
    """One row per marker occurrence, across every provision."""
    rows: list[tuple[object, ...]] = []
    for provision in provisions:
        provision_id = str(provision["provision_id"])
        text = str(provision["text"])
        for category, markers in MARKER_SETS:
            for label, match in iter_matches(text, markers):
                span, offset = match.group(0), match.start()
                # PROTOCOL.md: a span that is not a verbatim substring of its
                # input is a failed extraction, never silently accepted.
                if text[offset : offset + len(span)] != span:
                    raise SystemExit(
                        f"{provision_id}: marker {label!r} produced span {span!r} "
                        f"that is not the text at offset {offset}"
                    )
                rows.append((provision_id, category, label, span, offset))
    return rows


def _write_table(
    connection: duckdb.DuckDBPyConnection,
    name: str,
    columns: tuple[tuple[str, str], ...],
    rows: list[tuple[object, ...]],
    tables_dir: Path,
) -> Path:
    declaration = ", ".join(f'"{column}" {sql_type}' for column, sql_type in columns)
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(f'CREATE OR REPLACE TABLE "{name}" ({declaration})')
    if rows:
        connection.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})', rows)

    destination = tables_dir / f"{name}.parquet"
    connection.execute(
        f"COPY \"{name}\" TO '{destination.as_posix().replace(chr(39), chr(39) * 2)}' (FORMAT PARQUET)"
    )
    return destination


def build_tables(provisions_path: Path, tables_dir: Path) -> dict[str, int]:
    provisions = load_provisions(provisions_path)
    candidates = shortlist(provisions)

    known_ids = {str(provision["provision_id"]) for provision in provisions}
    orphans = {str(candidate["provision_id"]) for candidate in candidates} - known_ids
    if orphans:
        raise SystemExit(f"candidates reference unknown provisions: {sorted(orphans)[:5]}")

    tables = (
        ("provisions", PROVISION_COLUMNS, provision_rows(provisions)),
        ("candidates", CANDIDATE_COLUMNS, candidate_rows(candidates)),
        ("marker_hits", MARKER_HIT_COLUMNS, marker_hit_rows(provisions)),
        ("markers", MARKER_COLUMNS, marker_rows()),
    )

    tables_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    try:
        for name, columns, rows in tables:
            _write_table(connection, name, columns, rows, tables_dir)
    finally:
        connection.close()

    return {name: len(rows) for name, _columns, rows in tables}
