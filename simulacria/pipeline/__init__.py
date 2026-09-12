"""The data layers: bronze bytes, silver records, gold tables.

Medallion order, and what each layer may assume about the one below it:

``bronze``
    Original bytes as fetched, wrapped in an envelope that carries the URL, the
    retrieval time and the SHA-256 of the payload. Never rewritten. A domain
    adapter (``simulacria.domains``) knows how to read its own bronze envelope.

``silver``
    Parsed records -- one provision or passage per row -- built from bronze and
    verified against a pool contract before they are written. Rebuilding silver
    from the same bronze must reproduce the same rows.

``tables`` / ``store`` / ``gold``
    Projections for analysis: Parquet tables, and the DuckDB database that holds
    them beside the research tables of recorded runs. Every gold artifact can be
    rebuilt from bronze plus code; none of it is evidence in its own right.

Run evidence is the exception to the medallion flow. Raw API responses and the
JSONL records of a run are written once by ``simulacria.generation`` and are not
derived from bronze; they are irreplaceable, and gold only projects them.
"""

from __future__ import annotations
