from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.ingestion import load_las


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROVENANCE_PATH = PROJECT_ROOT / "data" / "source" / "las" / "provenance.json"
BRONZE_PATH = PROJECT_ROOT / "data" / "bronze" / "las" / "sfs-1982-80.json"

BRONZE_COLUMNS = [
    "document_id",
    "title",
    "version",
    "issued_at",
    "published_at",
    "retrieved_at",
    "source_page_url",
    "source_data_url",
    "source_sha256",
    "text",
    "html",
]
BRONZE_DTYPES = {
    "document_id": "string",
    "title": "string",
    "version": "string",
    "issued_at": "string",
    "published_at": "string",
    "retrieved_at": "string",
    "source_page_url": "string",
    "source_data_url": "string",
    "source_sha256": "string",
    "text": "string",
    "html": "string",
}


def build_bronze_df() -> pd.DataFrame:
    source = load_las()
    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))

    if provenance["raw_sha256"] != source.raw_sha256:
        raise ValueError("LAS provenance hash does not match the canonical source")
    if provenance["document_id"] != source.document_id:
        raise ValueError("LAS provenance document ID does not match the source")

    source_df = pd.DataFrame(
        [
            {
                "document_id": source.document_id,
                "title": source.title,
                "version": source.version,
                "issued_at": source.issued_at,
                "published_at": source.published_at,
                "text": source.text,
                "html": source.html,
            }
        ]
    )

    provenance_df = pd.DataFrame(
        [
            {
                "document_id": provenance["document_id"],
                "retrieved_at": provenance["retrieved_at"],
                "source_page_url": provenance["source_page_url"],
                "source_data_url": provenance["source_data_url"],
                "source_sha256": provenance["raw_sha256"],
            }
        ]
    )

    bronze_df = source_df.merge(
        provenance_df,
        on="document_id",
        how="left",
        validate="one_to_one",
        indicator="provenance_match",
    )
    if bronze_df["provenance_match"].ne("both").any():
        raise ValueError("Bronze source is missing provenance metadata")

    bronze_df = bronze_df.astype(BRONZE_DTYPES)
    bronze_df = bronze_df.loc[:, BRONZE_COLUMNS]

    return bronze_df


def write_bronze_df(bronze_df: pd.DataFrame, path: Path = BRONZE_PATH) -> None:
    if len(bronze_df) != 1:
        raise ValueError("Bronze LAS must contain exactly one document row")

    path.parent.mkdir(parents=True, exist_ok=True)
    record = bronze_df.iloc[0].to_dict()
    serialized = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    path.write_text(serialized, encoding="utf-8", newline="\n")
