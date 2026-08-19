from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .gold import MAX_RETRIEVAL_CHARS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUALITY_PATH = PROJECT_ROOT / "data" / "quality" / "las" / "summary.jsonl"

QUALITY_COLUMNS = [
    "document_id",
    "kind",
    "provision_count",
    "min_text_chars",
    "max_text_chars",
    "chunk_count",
    "max_retrieval_chars",
]


def validate_las_data(
    bronze_df: pd.DataFrame,
    silver_df: pd.DataFrame,
    gold_df: pd.DataFrame,
) -> None:
    if len(bronze_df) != 1:
        raise ValueError("Data Quality failed: Bronze must contain one LAS document")

    if silver_df.empty:
        raise ValueError("Data Quality failed: Silver contains no provisions")
    if silver_df["provision_id"].isna().any():
        raise ValueError("Data Quality failed: Silver has missing provision IDs")
    if silver_df["provision_id"].duplicated().any():
        raise ValueError("Data Quality failed: Silver has duplicate provision IDs")
    if silver_df["text"].isna().any() or silver_df["text"].eq("").any():
        raise ValueError("Data Quality failed: Silver has empty legal text")

    if gold_df.empty:
        raise ValueError("Data Quality failed: Gold contains no retrieval chunks")
    if gold_df["chunk_id"].isna().any():
        raise ValueError("Data Quality failed: Gold has missing chunk IDs")
    if gold_df["chunk_id"].duplicated().any():
        raise ValueError("Data Quality failed: Gold has duplicate chunk IDs")
    if gold_df["retrieval_char_count"].gt(MAX_RETRIEVAL_CHARS).any():
        raise ValueError(
            "Data Quality failed: Gold has an oversized retrieval chunk"
        )

    silver_provision_ids = set(silver_df["provision_id"])
    gold_provision_ids = set(gold_df["provision_id"])
    if silver_provision_ids != gold_provision_ids:
        raise ValueError(
            "Data Quality failed: Gold does not represent all Silver provisions"
        )

    silver_hashes = set(silver_df["source_sha256"])
    gold_hashes = set(gold_df["source_sha256"])
    bronze_hashes = set(bronze_df["source_sha256"])
    if silver_hashes != bronze_hashes or gold_hashes != bronze_hashes:
        raise ValueError("Data Quality failed: source hashes differ between layers")

    reconstructed_text = (
        gold_df.sort_values(["provision_id", "part"])
        .groupby("provision_id", sort=False)["content"]
        .agg("\n\n".join)
    )
    silver_text = silver_df.set_index("provision_id")["text"]
    if reconstructed_text.to_dict() != silver_text.to_dict():
        raise ValueError("Data Quality failed: Gold cannot reconstruct Silver text")


def build_quality_df(
    silver_df: pd.DataFrame, gold_df: pd.DataFrame
) -> pd.DataFrame:
    silver_profile_df = silver_df.copy()
    silver_profile_df["text_char_count"] = silver_profile_df["text"].str.len()
    silver_profile_df = silver_profile_df.groupby(
        ["document_id", "kind"], as_index=False
    ).agg(
        provision_count=("provision_id", "nunique"),
        min_text_chars=("text_char_count", "min"),
        max_text_chars=("text_char_count", "max"),
    )

    gold_profile_df = gold_df.groupby(
        ["document_id", "kind"], as_index=False
    ).agg(
        chunk_count=("chunk_id", "nunique"),
        max_retrieval_chars=("retrieval_char_count", "max"),
    )

    quality_df = silver_profile_df.merge(
        gold_profile_df,
        on=["document_id", "kind"],
        how="left",
        validate="one_to_one",
        indicator="gold_profile_match",
    )
    if quality_df["gold_profile_match"].ne("both").any():
        raise ValueError("Quality profile is missing Gold aggregation rows")

    quality_df = quality_df.astype(
        {
            "document_id": "string",
            "kind": "string",
            "provision_count": "int64",
            "min_text_chars": "int64",
            "max_text_chars": "int64",
            "chunk_count": "int64",
            "max_retrieval_chars": "int64",
        }
    )
    quality_df = quality_df.loc[:, QUALITY_COLUMNS]

    return quality_df


def write_quality_df(
    quality_df: pd.DataFrame, path: Path = QUALITY_PATH
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        json.dumps(record, ensure_ascii=False)
        for record in quality_df.to_dict(orient="records")
    ]
    path.write_text("\n".join(records) + "\n", encoding="utf-8", newline="\n")
