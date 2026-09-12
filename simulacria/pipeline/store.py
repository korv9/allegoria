"""GOLD. Read access to the Parquet analysis tables.

Not measurement. These tables hold marker hits and candidate rankings -- the
output of the selection heuristics -- and exist so a human can interrogate the
shortlist with SQL instead of reading a terminal dump.

`scripts/pipeline/build_tables.py` writes them; everything else reads them through here.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

TABLE_NAMES = ("provisions", "candidates", "marker_hits", "markers")


def connect(tables_dir: Path) -> duckdb.DuckDBPyConnection:
    """An in-memory DuckDB with each Parquet file registered as a view."""
    missing = [name for name in TABLE_NAMES if not (tables_dir / f"{name}.parquet").is_file()]
    if missing:
        raise SystemExit(
            f"missing table(s) {missing} in {tables_dir}. Run scripts/pipeline/build_tables.py first."
        )

    connection = duckdb.connect()
    for name in TABLE_NAMES:
        source = (tables_dir / f"{name}.parquet").as_posix().replace("'", "''")
        connection.execute(f"CREATE VIEW \"{name}\" AS SELECT * FROM read_parquet('{source}')")
    return connection


def query(tables_dir: Path, sql: str) -> tuple[list[str], list[tuple[object, ...]]]:
    """Run one statement and return (column names, rows)."""
    connection = connect(tables_dir)
    try:
        result = connection.execute(sql)
        columns = [description[0] for description in result.description or []]
        return columns, result.fetchall()
    finally:
        connection.close()
