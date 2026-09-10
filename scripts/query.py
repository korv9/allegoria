"""Run SQL against the local Parquet tables.

A thin wrapper over DuckDB: it registers `provisions`, `candidates` and
`marker_hits` as views over `data/local/tables/*.parquet`, runs the SQL you give
it, and prints the result. No ORM, no query builder, no schema layer.

    python scripts/query.py -c "select determinacy, count(*) from candidates group by 1"
    python scripts/query.py < docs/some_query.sql
    echo "describe provisions" | python scripts/query.py

Example queries live in `docs/queries.md`.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = PROJECT_ROOT / "data" / "local" / "tables"
TABLES = ("provisions", "candidates", "marker_hits", "markers")


def connect(tables_dir: Path) -> duckdb.DuckDBPyConnection:
    missing = [name for name in TABLES if not (tables_dir / f"{name}.parquet").is_file()]
    if missing:
        raise SystemExit(
            f"missing table(s) {missing} in {tables_dir}. Run scripts/build_tables.py first."
        )

    connection = duckdb.connect()
    for name in TABLES:
        source = (tables_dir / f"{name}.parquet").as_posix()
        connection.execute(f"CREATE VIEW \"{name}\" AS SELECT * FROM read_parquet('{source}')")
    return connection


def format_table(columns: list[str], rows: list[tuple[object, ...]], max_width: int) -> str:
    cells = [[_cell(value, max_width) for value in row] for row in rows]
    widths = [
        max(len(column), *(len(row[index]) for row in cells)) if cells else len(column)
        for index, column in enumerate(columns)
    ]

    lines = [
        "  ".join(column.ljust(width) for column, width in zip(columns, widths)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in cells)
    return "\n".join(lines)


def _cell(value: object, max_width: int) -> str:
    text = "" if value is None else str(value).replace("\n", " ")
    return text if len(text) <= max_width else text[: max_width - 1] + "…"


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--command", help="SQL to run; omit to read stdin")
    parser.add_argument("--pool", choices=("v1", "v2"), default="v1")
    parser.add_argument("--tables-dir", type=Path, help="override the pool's table directory")
    parser.add_argument("--max-width", type=int, default=60, help="truncate wide cells")
    args = parser.parse_args()

    tables_dir = args.tables_dir or (
        TABLES_DIR if args.pool == "v1" else TABLES_DIR.with_name("tables_v2")
    )

    sql = args.command if args.command is not None else sys.stdin.read()
    if not sql.strip():
        raise SystemExit('no SQL given: pass -c "..." or pipe a query on stdin')

    connection = connect(tables_dir)
    try:
        result = connection.execute(sql)
        columns = [description[0] for description in result.description or []]
        rows = result.fetchall()
    finally:
        connection.close()

    if not columns:
        print("(no result set)")
        return

    print(format_table(columns, rows, args.max_width))
    print(f"\n{len(rows)} row(s)")


if __name__ == "__main__":
    main()
