from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.ingestion import parse_las_html


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "las" / "provisions.jsonl"

SILVER_COLUMNS = [
    "provision_id",
    "document_id",
    "kind",
    "source_anchor",
    "label",
    "heading",
    "order",
    "text",
    "subsection_anchors",
    "amendment_notes",
    "source_url",
    "source_sha256",
]


def build_silver_df(bronze_df: pd.DataFrame) -> pd.DataFrame:
    if len(bronze_df) != 1:
        raise ValueError("Silver LAS expects exactly one Bronze document row")

    document_id = bronze_df.loc[0, "document_id"]
    document_html = bronze_df.loc[0, "html"]

    provisions_df = parse_las_html(
        html=document_html,
        document_id=document_id,
    )
    provisions_df["provision_id"] = (
        provisions_df["document_id"] + ":" + provisions_df["provision_suffix"]
    )

    document_metadata_df = bronze_df.loc[
        :, ["document_id", "source_page_url", "source_sha256"]
    ]

    silver_df = provisions_df.merge(
        document_metadata_df,
        on="document_id",
        how="left",
        validate="many_to_one",
        indicator="document_match",
    )
    if silver_df["document_match"].ne("both").any():
        raise ValueError("Silver provisions are missing Bronze document metadata")

    silver_df["source_url"] = (
        silver_df["source_page_url"] + "#" + silver_df["source_anchor"]
    )
    silver_df["order"] = silver_df["order"].astype("int64")
    silver_df = silver_df.astype(
        {
            "provision_id": "string",
            "document_id": "string",
            "kind": "string",
            "source_anchor": "string",
            "label": "string",
            "heading": "string",
            "text": "string",
            "source_url": "string",
            "source_sha256": "string",
        }
    )
    silver_df = silver_df.loc[:, SILVER_COLUMNS]

    if silver_df["provision_id"].duplicated().any():
        raise ValueError("LAS HTML produces duplicate provision IDs")

    return silver_df


def write_silver_df(silver_df: pd.DataFrame, path: Path = SILVER_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        json.dumps(record, ensure_ascii=False)
        for record in silver_df.to_dict(orient="records")
    ]
    path.write_text("\n".join(records) + "\n", encoding="utf-8", newline="\n")
