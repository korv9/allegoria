from __future__ import annotations

import pandas as pd


CONTEXT_SCHEMA_VERSION = "1.0"
CONTEXT_COLUMNS = [
    "rank",
    "score",
    "chunk_id",
    "document_id",
    "provision_id",
    "label",
    "heading",
    "part",
    "content",
    "source_url",
    "source_sha256",
]


def build_context_packet(
    query: str,
    retriever: str,
    result_df: pd.DataFrame,
) -> dict[str, object]:
    if not query.strip():
        raise ValueError("Context query must not be empty")
    if not retriever.strip():
        raise ValueError("Context retriever must not be empty")
    if result_df.empty:
        raise ValueError("Cannot build context without retrieved chunks")

    missing_columns = set(CONTEXT_COLUMNS) - set(result_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Retrieval results are missing context columns: {missing}")

    context_df = result_df.loc[:, CONTEXT_COLUMNS].copy()
    _validate_context_df(context_df)

    chunks = []
    for row in context_df.to_dict(orient="records"):
        chunks.append(
            {
                "citation_id": f'source-{int(row["rank"]):02d}',
                "rank": int(row["rank"]),
                "score": float(row["score"]),
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "provision_id": row["provision_id"],
                "label": row["label"],
                "heading": row["heading"],
                "part": int(row["part"]),
                "content": row["content"],
                "source_url": row["source_url"],
                "source_sha256": row["source_sha256"],
            }
        )

    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "query": query,
        "retriever": retriever,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def format_context_text(context_packet: dict[str, object]) -> str:
    chunks = context_packet.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Context packet must contain retrieved chunks")

    sections = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError("Context packet contains an invalid chunk")

        required = {
            "citation_id",
            "provision_id",
            "label",
            "heading",
            "content",
            "source_url",
        }
        missing_fields = required - set(chunk)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Context chunk is missing fields: {missing}")

        sections.append(
            "\n".join(
                [
                    f'[{chunk["citation_id"]}]',
                    f'provision_id: {chunk["provision_id"]}',
                    f'label: {chunk["label"]}',
                    f'heading: {chunk["heading"]}',
                    f'source_url: {chunk["source_url"]}',
                    "content:",
                    str(chunk["content"]),
                ]
            )
        )

    return "\n\n".join(sections)


def _validate_context_df(context_df: pd.DataFrame) -> None:
    required_text_columns = [
        "chunk_id",
        "document_id",
        "provision_id",
        "content",
        "source_url",
        "source_sha256",
    ]
    if context_df[required_text_columns].isna().any().any():
        raise ValueError("Retrieval results have missing context values")
    if context_df[required_text_columns].eq("").any().any():
        raise ValueError("Retrieval results have empty context values")
    if context_df[["rank", "score", "part"]].isna().any().any():
        raise ValueError("Retrieval results have missing numeric context values")
    if context_df["chunk_id"].duplicated().any():
        raise ValueError("Retrieval results have duplicate chunks")
    if context_df["part"].lt(1).any():
        raise ValueError("Retrieval result chunk parts must be positive")

    expected_ranks = list(range(1, len(context_df) + 1))
    if context_df["rank"].tolist() != expected_ranks:
        raise ValueError("Retrieval result ranks must be consecutive from one")
