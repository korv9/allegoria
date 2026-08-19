from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = PROJECT_ROOT / "data" / "gold" / "las" / "chunks.jsonl"
MAX_RETRIEVAL_CHARS = 2_000

GOLD_COLUMNS = [
    "chunk_id",
    "document_id",
    "provision_id",
    "kind",
    "source_anchor",
    "label",
    "heading",
    "part",
    "part_count",
    "content",
    "content_char_count",
    "retrieval_text",
    "retrieval_char_count",
    "source_url",
    "source_sha256",
]
GOLD_DTYPES = {
    "chunk_id": "string",
    "document_id": "string",
    "provision_id": "string",
    "kind": "string",
    "source_anchor": "string",
    "label": "string",
    "heading": "string",
    "part": "int64",
    "part_count": "int64",
    "content": "string",
    "content_char_count": "int64",
    "retrieval_text": "string",
    "retrieval_char_count": "int64",
    "source_url": "string",
    "source_sha256": "string",
}


def build_gold_df(
    bronze_df: pd.DataFrame, silver_df: pd.DataFrame
) -> pd.DataFrame:
    if len(bronze_df) != 1:
        raise ValueError("Gold LAS expects exactly one Bronze document row")

    document_metadata_df = bronze_df.loc[:, ["document_id", "title"]]
    enriched_provisions_df = silver_df.merge(
        document_metadata_df,
        on="document_id",
        how="left",
        validate="many_to_one",
        indicator="document_match",
    )
    if enriched_provisions_df["document_match"].ne("both").any():
        raise ValueError("Gold provisions are missing Bronze document metadata")

    enriched_provisions_df["context"] = _build_context_column(
        enriched_provisions_df
    )

    chunk_parts_df = pd.DataFrame(_chunk_records(enriched_provisions_df))
    provision_metadata_df = enriched_provisions_df.loc[
        :,
        [
            "provision_id",
            "document_id",
            "kind",
            "source_anchor",
            "label",
            "heading",
            "title",
            "source_url",
            "source_sha256",
        ],
    ]

    gold_df = chunk_parts_df.merge(
        provision_metadata_df,
        on="provision_id",
        how="left",
        validate="many_to_one",
        indicator="provision_match",
    )
    if gold_df["provision_match"].ne("both").any():
        raise ValueError("Gold chunks are missing Silver provision metadata")

    gold_df["chunk_id"] = (
        gold_df["provision_id"]
        + ":chunk-"
        + gold_df["part"].astype("string").str.zfill(2)
    )
    gold_df["content_char_count"] = gold_df["content"].str.len()
    gold_df["retrieval_text"] = gold_df["context"] + "\n\n" + gold_df["content"]
    gold_df["retrieval_char_count"] = gold_df["retrieval_text"].str.len()
    gold_df = gold_df.astype(GOLD_DTYPES)
    gold_df = gold_df.loc[:, GOLD_COLUMNS]

    oversized = gold_df["retrieval_char_count"] > MAX_RETRIEVAL_CHARS
    if oversized.any():
        chunk_id = gold_df.loc[oversized, "chunk_id"].iloc[0]
        raise ValueError(f"Gold chunk exceeds size limit: {chunk_id}")

    return gold_df


def write_gold_df(gold_df: pd.DataFrame, path: Path = GOLD_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        json.dumps(record, ensure_ascii=False)
        for record in gold_df.to_dict(orient="records")
    ]
    path.write_text("\n".join(records) + "\n", encoding="utf-8", newline="\n")


def _chunk_records(provisions_df: pd.DataFrame) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for provision in provisions_df.to_dict(orient="records"):
        context = provision["context"]
        max_content_chars = MAX_RETRIEVAL_CHARS - len(context) - 2
        content_parts = _split_content(provision["text"], max_content_chars)

        for part, content in enumerate(content_parts, start=1):
            records.append(
                {
                    "provision_id": provision["provision_id"],
                    "part": part,
                    "part_count": len(content_parts),
                    "content": content,
                    "context": context,
                }
            )

    return records


def _build_context_column(provisions_df: pd.DataFrame) -> pd.Series:
    context = provisions_df["title"].astype("string")

    has_heading = provisions_df["heading"].ne("")
    heading_is_new = provisions_df["heading"].ne(provisions_df["title"])
    add_heading = has_heading & heading_is_new
    context = context.mask(
        add_heading,
        context + "\n" + provisions_df["heading"],
    )

    has_label = provisions_df["label"].ne("")
    label_is_not_title = provisions_df["label"].ne(provisions_df["title"])
    label_is_not_heading = provisions_df["label"].ne(provisions_df["heading"])
    add_label = has_label & label_is_not_title & label_is_not_heading
    context = context.mask(
        add_label,
        context + "\n" + provisions_df["label"],
    )

    return context


def _split_content(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        if len(block) > max_chars:
            raise ValueError(
                f"An indivisible legal text block exceeds {max_chars} characters"
            )

        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            parts.append(current)
            current = block

    if current:
        parts.append(current)
    return parts
