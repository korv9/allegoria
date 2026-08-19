from __future__ import annotations

import re
import sqlite3
from types import TracebackType

import pandas as pd

from .gold import RETRIEVAL_COLUMNS, load_gold_df


RESULT_COLUMNS = ["rank", "score", *RETRIEVAL_COLUMNS]
RESULT_DTYPES = {
    "rank": "int64",
    "score": "float64",
    "chunk_id": "string",
    "document_id": "string",
    "provision_id": "string",
    "kind": "string",
    "label": "string",
    "heading": "string",
    "part": "int64",
    "content": "string",
    "retrieval_text": "string",
    "source_url": "string",
    "source_sha256": "string",
}

CREATE_INDEX_SQL = """
CREATE VIRTUAL TABLE chunks USING fts5(
    chunk_id UNINDEXED,
    document_id UNINDEXED,
    provision_id UNINDEXED,
    kind UNINDEXED,
    label UNINDEXED,
    heading UNINDEXED,
    part UNINDEXED,
    content UNINDEXED,
    retrieval_text,
    source_url UNINDEXED,
    source_sha256 UNINDEXED,
    tokenize = 'unicode61'
)
"""

SEARCH_SQL = """
SELECT
    -bm25(chunks) AS score,
    chunk_id,
    document_id,
    provision_id,
    kind,
    label,
    heading,
    part,
    content,
    retrieval_text,
    source_url,
    source_sha256
FROM chunks
WHERE chunks MATCH ?
ORDER BY bm25(chunks), chunk_id
LIMIT ?
"""


class LexicalRetriever:
    def __init__(self, gold_df: pd.DataFrame) -> None:
        self._connection = sqlite3.connect(":memory:")
        self._connection.execute(CREATE_INDEX_SQL)

        index_df = gold_df.loc[:, RETRIEVAL_COLUMNS]
        placeholders = ", ".join("?" for _ in RETRIEVAL_COLUMNS)
        insert_sql = f"INSERT INTO chunks VALUES ({placeholders})"
        rows = index_df.itertuples(index=False, name=None)
        self._connection.executemany(insert_sql, rows)

    def search(self, query: str, top_k: int = 5) -> pd.DataFrame:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        fts_query = _build_fts_query(query)
        rows = self._connection.execute(
            SEARCH_SQL,
            (fts_query, top_k),
        ).fetchall()

        result_df = pd.DataFrame(rows, columns=RESULT_COLUMNS[1:])
        result_df.insert(0, "rank", range(1, len(result_df) + 1))
        result_df = result_df.astype(RESULT_DTYPES)
        result_df = result_df.loc[:, RESULT_COLUMNS]

        return result_df

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> LexicalRetriever:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def search_las(query: str, top_k: int = 5) -> pd.DataFrame:
    gold_df = load_gold_df()
    with LexicalRetriever(gold_df) as retriever:
        return retriever.search(query=query, top_k=top_k)


def _build_fts_query(query: str) -> str:
    tokens = re.findall(r"[^\W_]+", query.casefold())
    unique_tokens = list(dict.fromkeys(tokens))

    if not unique_tokens:
        raise ValueError("Retrieval query must contain at least one word or number")

    return " OR ".join(f'"{token}"*' for token in unique_tokens)
