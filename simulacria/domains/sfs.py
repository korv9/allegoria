"""Swedish statute (SFS), resolved through the committed bronze snapshots.

The lineage check is the point of this adapter. Before a passage is used, the
original XML bytes are re-hashed, the bronze envelope is compared against those
bytes field by field, and the HTML the parser sees is the HTML the XML carried.
A corpus that points at a document whose bytes have moved raises rather than
quietly measuring a different text.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree

from products.allegoria.sfs_parser import parse_sfs_html
from simulacria.domains.base import Domain, PassageSource, register

SOURCE_DIR = "data/source/sfs"
BRONZE_DIR = "data/bronze/sfs"


def resolve(passage_id: str, root: Path, _spec: dict) -> PassageSource:
    document_id, _, suffix = passage_id.partition(":")
    if (
        not suffix
        or not document_id.startswith("sfs-")
        or "/" in document_id
        or "\\" in document_id
    ):
        raise ValueError(f"invalid SFS passage id: {passage_id}")
    bronze = json.loads((root / BRONZE_DIR / f"{document_id}.json").read_text(encoding="utf-8"))
    raw = (root / SOURCE_DIR / f"{document_id}.xml").read_bytes()
    if sha256(raw).hexdigest() != bronze["source_sha256"]:
        raise ValueError(f"source hash mismatch: {passage_id}")
    if bronze["raw_xml"].encode("utf-8") != raw:
        raise ValueError(f"bronze payload mismatch: {passage_id}")
    if ElementTree.fromstring(raw).findtext("dokument/html") != bronze["html"]:
        raise ValueError(f"bronze HTML differs from the original XML: {passage_id}")
    if bronze["document_id"] != document_id:
        raise ValueError(f"bronze document mismatch: {passage_id}")
    matches = [
        p for p in parse_sfs_html(bronze["html"], document_id) if p["provision_suffix"] == suffix
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one provision for {passage_id}")
    return PassageSource(
        text=matches[0]["text"],
        document_title=bronze["title"],
        source_url=bronze["source_page_url"] + "#" + matches[0]["source_anchor"],
        source_sha256=bronze["source_sha256"],
    )


DOMAIN = register(
    Domain(
        name="sfs",
        language="sv",
        id_format="<document id>:<provision suffix>, e.g. sfs-1982-673:P13",
        resolve=resolve,
        source_dir=SOURCE_DIR,
        bronze_dir=BRONZE_DIR,
        notes="Bytes, bronze envelope and parsed HTML are cross-checked on every load.",
    )
)
