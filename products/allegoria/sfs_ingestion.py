"""Fetch a reproducible 50-law SFS corpus from Riksdagen."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

SEED_DOCUMENT_IDS = (
    "sfs-1982-80",
    "sfs-1976-580",
    "sfs-1977-480",
    "sfs-1982-673",
    "sfs-1995-584",
    "sfs-2008-567",
)
TARGET_DOCUMENT_COUNT = 50
DATA_URL_TEMPLATE = "https://data.riksdagen.se/dokument/{document_id}"
PAGE_URL_TEMPLATE = "https://data.riksdagen.se/dokument/{document_id}.html"
LIST_URL = "https://data.riksdagen.se/dokumentlista/"


def fetch_sfs_corpus(project_root: Path) -> list[dict[str, str | int | None]]:
    """Discover and fetch 50 laws, then materialize only after all validate."""
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    document_ids = discover_document_ids()
    raw_documents: dict[str, bytes] = {}
    bronze_documents: list[dict[str, str | int | None]] = []

    for document_id in document_ids:
        source_url = DATA_URL_TEMPLATE.format(document_id=document_id)
        raw_xml = _fetch_bytes(source_url, accept="application/xml")
        bronze = parse_sfs_xml(raw_xml, document_id, source_url, retrieved_at)
        raw_documents[document_id] = raw_xml
        bronze_documents.append(bronze)

    _write_corpus(project_root, raw_documents, bronze_documents, retrieved_at)
    return bronze_documents


def discover_document_ids() -> tuple[str, ...]:
    """Combine the domain seeds with recent laws from the SFS document list."""
    selected = list(SEED_DOCUMENT_IDS)
    selected_set = set(selected)
    page = 1

    while len(selected) < TARGET_DOCUMENT_COUNT:
        query = urlencode(
            {
                "doktyp": "sfs",
                "sort": "datum",
                "sortorder": "desc",
                "utformat": "json",
                "p": page,
            }
        )
        payload = json.loads(_fetch_bytes(f"{LIST_URL}?{query}", "application/json"))
        document_list = payload.get("dokumentlista")
        if not isinstance(document_list, dict):
            raise TypeError(f"SFS list page {page} has no dokumentlista object")
        documents = document_list.get("dokument")
        if not isinstance(documents, list) or not documents:
            raise ValueError(f"SFS list page {page} contains no documents")

        for document in documents:
            if not isinstance(document, dict):
                raise TypeError(f"SFS list page {page} contains an invalid document")
            document_id = _required_list_value(document, "dok_id", page)
            title = _required_list_value(document, "titel", page)
            if _is_law_title(title) and document_id not in selected_set:
                selected.append(document_id)
                selected_set.add(document_id)
                if len(selected) == TARGET_DOCUMENT_COUNT:
                    break
        page += 1

    return tuple(selected)


def parse_sfs_xml(
    raw_xml: bytes,
    expected_document_id: str,
    source_url: str,
    retrieved_at: str,
) -> dict[str, str | int | None]:
    """Validate one Riksdagen response and create its full Bronze record."""
    root = ElementTree.fromstring(raw_xml)
    document = root.find("dokument")
    if document is None:
        raise ValueError(f"{expected_document_id}: XML contains no dokument element")

    document_id = _required_text(document, "dok_id")
    if document_id != expected_document_id:
        raise ValueError(
            f"Document ID mismatch: requested {expected_document_id}, got {document_id}"
        )
    source_type = _required_text(document, "typ")
    source_subtype = _required_text(document, "subtyp")
    if source_type != "sfs" or source_subtype != "sfst":
        raise ValueError(
            f"{document_id}: expected SFS full text, got {source_type}/{source_subtype}"
        )

    source_sha256 = hashlib.sha256(raw_xml).hexdigest()
    raw_xml_text = raw_xml.decode("utf-8")
    if raw_xml_text.encode("utf-8") != raw_xml:
        raise ValueError(f"{document_id}: XML is not lossless UTF-8")

    return {
        "document_snapshot_id": f"{document_id}:{source_sha256}",
        "document_id": document_id,
        "designation": _required_text(document, "beteckning"),
        "title": _required_text(document, "titel"),
        "version": _optional_text(document, "subtitel"),
        "department": _required_text(document, "organ"),
        "source_type": source_type,
        "source_subtype": source_subtype,
        "issued_at": _required_text(document, "datum"),
        "published_at": _required_text(document, "publicerad"),
        "retrieved_at": retrieved_at,
        "source_page_url": PAGE_URL_TEMPLATE.format(document_id=document_id),
        "source_data_url": source_url,
        "source_raw_file": f"{document_id}.xml",
        "source_sha256": source_sha256,
        "payload_size_bytes": len(raw_xml),
        "text": _required_payload(document, "text"),
        "html": _required_payload(document, "html"),
        "raw_xml": raw_xml_text,
    }


def _fetch_bytes(url: str, accept: str) -> bytes:
    request = Request(
        url,
        headers={"Accept": accept, "User-Agent": "allegoria-source-ingestion/0.2"},
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"GET {url} returned HTTP {response.status}")
        payload = response.read()
    if not payload:
        raise ValueError(f"GET {url} returned an empty response")
    return payload


def _is_law_title(title: str) -> bool:
    normalized = title.casefold()
    return "förordning" not in normalized and (
        "lag (" in normalized or "balk (" in normalized
    )


def _required_list_value(document: dict[str, object], key: str, page: int) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"SFS list page {page} document is missing {key}")
    return value.strip()


def _required_text(document: ElementTree.Element, tag: str) -> str:
    value = document.findtext(tag)
    if value is None or not value.strip():
        raise ValueError(f"SFS document is missing required field {tag}")
    return value.strip()


def _required_payload(document: ElementTree.Element, tag: str) -> str:
    value = document.findtext(tag)
    if value is None or not value.strip():
        raise ValueError(f"SFS document is missing required payload {tag}")
    return value


def _optional_text(document: ElementTree.Element, tag: str) -> str | None:
    value = document.findtext(tag)
    return value.strip() if value is not None and value.strip() else None


def _write_corpus(
    project_root: Path,
    raw_documents: dict[str, bytes],
    bronze_documents: list[dict[str, str | int | None]],
    retrieved_at: str,
) -> None:
    source_dir = project_root / "data/source/sfs"
    bronze_dir = project_root / "data/bronze/sfs"
    source_dir.mkdir(parents=True, exist_ok=True)
    bronze_dir.mkdir(parents=True, exist_ok=True)
    selected_ids = {str(document["document_id"]) for document in bronze_documents}

    for existing in source_dir.glob("*.xml"):
        if existing.stem not in selected_ids:
            existing.unlink()
    for existing in bronze_dir.glob("*.json"):
        if existing.stem not in selected_ids:
            existing.unlink()

    for bronze in bronze_documents:
        document_id = str(bronze["document_id"])
        (source_dir / f"{document_id}.xml").write_bytes(raw_documents[document_id])
        (bronze_dir / f"{document_id}.json").write_text(
            json.dumps(bronze, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "dataset_id": "swedish-law-50",
        "retrieved_at": retrieved_at,
        "source": "Sveriges riksdag open data",
        "selection": {
            "target_count": TARGET_DOCUMENT_COUNT,
            "seed_document_ids": list(SEED_DOCUMENT_IDS),
            "fill": "newest SFS titles containing 'lag (' or 'balk ('; regulations excluded",
        },
        "documents": [
            {
                "document_id": bronze["document_id"],
                "title": bronze["title"],
                "version": bronze["version"],
                "source_data_url": bronze["source_data_url"],
                "raw_file": bronze["source_raw_file"],
                "raw_sha256": bronze["source_sha256"],
            }
            for bronze in bronze_documents
        ],
    }
    (source_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    records = fetch_sfs_corpus(Path.cwd())
    print(
        f"SFS INGESTION | fetched {len(records)} laws | "
        "source: exact XML | bronze: full JSON payload"
    )
