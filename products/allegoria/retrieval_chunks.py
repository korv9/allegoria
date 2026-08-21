"""Deterministic, source-structure-aware chunking for legal provisions."""

from __future__ import annotations

MAX_RETRIEVAL_CHARS = 2_000
AI_SEARCH_MAX_SOURCE_BYTES = 32_764
CHUNKING_STRATEGY = "logical_blocks_v1"


def build_retrieval_context(
    document_title: str,
    chapter: str,
    heading: str,
    label: str,
) -> str:
    """Join non-empty, non-repeated legal hierarchy labels in source order."""
    context_lines: list[str] = []
    for value in (document_title, chapter, heading, label):
        normalized = value.strip()
        if normalized and normalized not in context_lines:
            context_lines.append(normalized)

    if not context_lines:
        raise ValueError("Retrieval context must contain source hierarchy")
    return "\n".join(context_lines)


def split_legal_content(
    text: str,
    retrieval_context: str,
    max_retrieval_chars: int = MAX_RETRIEVAL_CHARS,
) -> list[str]:
    """Keep a provision whole or split greedily at preserved blank lines."""
    if not text:
        raise ValueError("Legal content must not be empty")
    if not retrieval_context:
        raise ValueError("Retrieval context must not be empty")

    separator = "\n\n"
    max_content_chars = max_retrieval_chars - len(retrieval_context) - len(separator)
    if max_content_chars <= 0:
        raise ValueError("Retrieval context leaves no room for legal content")
    if len(text) <= max_content_chars:
        return [text]

    parts: list[str] = []
    current = ""
    for block in text.split(separator):
        if len(block) > max_content_chars:
            raise ValueError(
                "An indivisible legal text block exceeds the retrieval size limit"
            )

        candidate = block if not current else f"{current}{separator}{block}"
        if len(candidate) <= max_content_chars:
            current = candidate
        else:
            parts.append(current)
            current = block

    if current:
        parts.append(current)
    if separator.join(parts) != text:
        raise ValueError("Chunking did not preserve the complete provision text")
    return parts


def build_chunk_part_records(
    provision_id: str,
    document_title: str,
    chapter: str,
    heading: str,
    label: str,
    text: str,
) -> list[dict[str, object]]:
    """Create ordered chunk-part records for one Silver provision."""
    context = build_retrieval_context(document_title, chapter, heading, label)
    content_parts = split_legal_content(text, context)
    return [
        {
            "provision_id": provision_id,
            "part": part,
            "part_count": len(content_parts),
            "retrieval_context": context,
            "content": content,
        }
        for part, content in enumerate(content_parts, start=1)
    ]
