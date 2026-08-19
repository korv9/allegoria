from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.lakehouse.gold import GOLD_PATH


RETRIEVAL_COLUMNS = [
    "chunk_id",
    "document_id",
    "provision_id",
    "kind",
    "label",
    "heading",
    "part",
    "content",
    "retrieval_text",
    "source_url",
    "source_sha256",
]
RETRIEVAL_DTYPES = {
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


def load_gold_df(path: Path = GOLD_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Gold retrieval data does not exist: {path}")
    if path.stat().st_size == 0:
        raise ValueError("Gold retrieval data is empty")

    gold_df = pd.read_json(path, lines=True)

    missing_columns = set(RETRIEVAL_COLUMNS) - set(gold_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Gold retrieval data is missing columns: {missing}")

    gold_df = gold_df.loc[:, RETRIEVAL_COLUMNS]
    gold_df = gold_df.astype(RETRIEVAL_DTYPES)

    if gold_df["chunk_id"].isna().any():
        raise ValueError("Gold retrieval data has missing chunk IDs")
    if gold_df["chunk_id"].duplicated().any():
        raise ValueError("Gold retrieval data has duplicate chunk IDs")
    if gold_df["retrieval_text"].isna().any():
        raise ValueError("Gold retrieval data has missing retrieval text")
    if gold_df["retrieval_text"].eq("").any():
        raise ValueError("Gold retrieval data has empty retrieval text")

    return gold_df
