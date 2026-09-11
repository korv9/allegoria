"""Load explicitly drafted source slots from hash-verified, committed legal text.

No selection heuristics. Draft annotations remain drafts until a human reviews them.
"""

import json
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree

import yaml

from products.allegoria.sfs_parser import parse_sfs_html


def load_source_slots(path: Path, root: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not data.get("passages"):
        raise ValueError("source-slot corpus requires schema_version 1 and passages")
    status = data.get("annotation_status")
    if status != "assistant_draft_requires_human_review":
        raise ValueError("unsupported annotation status; human review needs its own evidence")
    result = []
    seen = set()
    for spec in data["passages"]:
        pid = spec["passage_id"]
        if pid in seen:
            raise ValueError(f"duplicate source passage: {pid}")
        seen.add(pid)
        document_id, suffix = pid.split(":", 1)
        if not document_id.startswith("sfs-") or "/" in document_id or "\\" in document_id:
            raise ValueError(f"invalid document ID: {document_id}")
        bronze = json.loads(
            (root / f"data/bronze/sfs/{document_id}.json").read_text(encoding="utf-8")
        )
        raw = (root / f"data/source/sfs/{document_id}.xml").read_bytes()
        if sha256(raw).hexdigest() != bronze["source_sha256"]:
            raise ValueError(f"source hash mismatch: {pid}")
        if bronze["raw_xml"].encode("utf-8") != raw:
            raise ValueError(f"Bronze payload mismatch: {pid}")
        if ElementTree.fromstring(raw).findtext("dokument/html") != bronze["html"]:
            raise ValueError(f"Bronze HTML differs from original XML: {pid}")
        if bronze["document_id"] != document_id:
            raise ValueError(f"Bronze document mismatch: {pid}")
        provisions = parse_sfs_html(bronze["html"], document_id)
        matches = [p for p in provisions if p["provision_suffix"] == suffix]
        if len(matches) != 1:
            raise ValueError(f"expected one source provision: {pid}")
        text = matches[0]["text"]
        slots = spec["slots"]
        if not slots or len({s["slot_id"] for s in slots}) != len(slots):
            raise ValueError(f"missing or duplicate slots: {pid}")
        for slot in slots:
            if slot["kind"] not in {"modality", "actor", "condition", "deadline", "exception"}:
                raise ValueError(f"unknown slot kind: {slot['kind']}")
            if slot["attaches_to"] not in {"duty", "exception"}:
                raise ValueError(f"unknown attachment: {pid}")
            if not slot["quote"] or text.count(slot["quote"]) != 1:
                raise ValueError(f"slot quote must occur exactly once: {pid}/{slot['slot_id']}")
        result.append(
            {
                **spec,
                "text": text,
                "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
                "source_sha256": bronze["source_sha256"],
                "document_title": bronze["title"],
                "source_url": bronze["source_page_url"] + "#" + matches[0]["source_anchor"],
                "annotation_status": status,
            }
        )
    return result
