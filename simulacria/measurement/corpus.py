"""Load an annotated corpus: passages, their lineage, and their draft slots.

One loader for every domain. What a passage id resolves to is the adapter's
business (`simulacria.domains`); what a slot may say is this module's, and it is
the same for every corpus so that two datasets stay comparable.

No selection heuristics are involved, here or anywhere downstream of it: slots
are hand-drafted and stay drafts until a human reviews them.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import yaml

from simulacria.domains import get
from simulacria.domains.base import ATTACHMENTS, SLOT_KINDS

SCHEMA_VERSION = 2
DRAFT_STATUS = "assistant_draft_requires_human_review"

# Baseline slot state for the `direction` metric (DIRECTION.md). Optional: a
# corpus annotates it slot by slot as it is hand-reviewed, and a corpus that has
# not started still loads. The values are the ladder rungs, never the selection
# side's marker determinacy, which is a different vocabulary ("unmarked").
DETERMINACY_STATES = frozenset({"specific", "vague", "absent"})
MODALITY_STATES = frozenset({"binding", "weak", "absent"})


def _slots(passage_id: str, spec: dict, defaults: list[dict], text: str) -> list[dict]:
    slots = spec.get("slots") or defaults
    if not slots:
        raise ValueError(f"{passage_id} has no slots and the corpus declares no default_slots")
    ids = [s["slot_id"] for s in slots]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate slot ids in {passage_id}")
    checked = []
    for slot in slots:
        if slot["kind"] not in SLOT_KINDS:
            raise ValueError(f"unknown slot kind {slot['kind']!r} in {passage_id}")
        if slot["attaches_to"] not in ATTACHMENTS:
            raise ValueError(f"unknown attachment {slot['attaches_to']!r} in {passage_id}")
        if not slot.get("question", "").strip():
            raise ValueError(f"slot {passage_id}/{slot['slot_id']} has no reading question")
        determinacy = slot.get("determinacy")
        if determinacy is not None and determinacy not in DETERMINACY_STATES:
            raise ValueError(
                f"unknown determinacy {determinacy!r} in {passage_id}/{slot['slot_id']}"
            )
        modality = slot.get("modality")
        if modality is not None and modality not in MODALITY_STATES:
            raise ValueError(f"unknown modality {modality!r} in {passage_id}/{slot['slot_id']}")
        quote = slot.get("quote")
        # A quote anchors the slot in the source text. Default slots describe a
        # question to ask of any passage, so they are allowed to carry none.
        if quote is not None and text.count(quote) != 1:
            raise ValueError(f"slot quote must occur exactly once: {passage_id}/{slot['slot_id']}")
        checked.append({**slot, "quote": quote})
    return checked


def load_corpus(path: Path, root: Path) -> list[dict]:
    """Every passage of one corpus file, with text resolved and slots validated."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path.name}: corpus requires schema_version {SCHEMA_VERSION}")
    if data.get("annotation_status") != DRAFT_STATUS:
        raise ValueError(f"{path.name}: human review needs its own evidence, not a status field")
    domain = get(data["domain"])
    defaults = data.get("default_slots") or []
    group = data.get("group") or data["domain"]
    passages, seen = [], set()
    for spec in data["passages"]:
        passage_id = spec["passage_id"]
        if passage_id in seen:
            raise ValueError(f"{path.name}: duplicate passage {passage_id}")
        seen.add(passage_id)
        source = domain.resolve(passage_id, root, spec)
        passages.append(
            {
                "passage_id": passage_id,
                "text_id": "source:" + passage_id,
                "generation": 0,
                "domain": domain.name,
                "language": domain.language,
                "group": spec.get("group", group),
                "rationale": spec.get("rationale", ""),
                "text": source.text,
                "text_sha256": sha256(source.text.encode("utf-8")).hexdigest(),
                "source_sha256": source.source_sha256,
                "document_title": source.document_title,
                "source_url": source.source_url,
                "annotation_status": DRAFT_STATUS,
                "slots": _slots(passage_id, spec, defaults, source.text),
            }
        )
    return passages


def load_corpora(paths: list[Path], root: Path) -> list[dict]:
    """Several corpus files as one passage list, rejecting ids that collide."""
    passages: list[dict] = []
    for path in paths:
        passages.extend(load_corpus(path, root))
    ids = [p["passage_id"] for p in passages]
    if len(ids) != len(set(ids)):
        raise ValueError("passage ids collide across corpora")
    return passages
