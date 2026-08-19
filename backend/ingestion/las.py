from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAS_SOURCE_PATH = PROJECT_ROOT / "data" / "source" / "las" / "sfs-1982-80.xml"
LAS_SOURCE_SHA256 = "a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b"


@dataclass(frozen=True)
class LegalSource:
    document_id: str
    title: str
    version: str
    issued_at: str
    published_at: str
    text: str
    raw_path: Path
    raw_sha256: str


def load_las() -> LegalSource:
    raw_source = LAS_SOURCE_PATH.read_bytes()
    source_hash = sha256(raw_source).hexdigest()

    if source_hash != LAS_SOURCE_SHA256:
        raise ValueError(
            "The canonical LAS source has changed: "
            f"expected {LAS_SOURCE_SHA256}, got {source_hash}"
        )

    root = ElementTree.fromstring(raw_source)
    document = root.find("dokument")

    if document is None:
        raise ValueError("The LAS source does not contain a dokument element")

    return LegalSource(
        document_id=_required_text(document, "dok_id"),
        title=_required_text(document, "titel"),
        version=_required_text(document, "subtitel"),
        issued_at=_required_text(document, "datum"),
        published_at=_required_text(document, "publicerad"),
        text=_required_text(document, "text"),
        raw_path=LAS_SOURCE_PATH,
        raw_sha256=source_hash,
    )


def _required_text(document: ElementTree.Element, field: str) -> str:
    value = document.findtext(field)

    if value is None:
        raise ValueError(f"The LAS source is missing the required field: {field}")

    return value

