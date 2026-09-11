"""A frozen exploratory design for ten-generation law and philosophical chains."""

import json
from hashlib import sha256
from pathlib import Path

import yaml

from simulacria.measurement.source_slots import load_source_slots

PHILOSOPHY_QUESTIONS = {
    "explicit_duty": "Uttrycker texten en uttrycklig plikt eller ett förbud för en handling?",
    "allowed_exception": (
        "Uttrycker texten ett faktiskt tillåtet undantag från en plikt eller ett förbud? "
        "Ett påstående att undantag saknas är inte ett tillåtet undantag."
    ),
    "exception_condition": "Anger texten ett villkor för ett faktiskt tillåtet undantag?",
}


def plan(root: Path) -> tuple[list[dict], list[dict]]:
    sources = load_source_slots(root / "corpus/law_probe_v1.yaml", root)
    for source in sources:
        source.update(group="statutory", pair_id=None)
    philosophy = yaml.safe_load((root / "corpus/philosophy_v1.yaml").read_text(encoding="utf-8"))
    for passage in philosophy["passages"]:
        if sha256(passage["text"].encode()).hexdigest() != passage["text_sha256"]:
            raise ValueError("philosophy source hash mismatch")
        sources.append(
            {
                **passage,
                "source_url": passage["source"],
                "source_sha256": None,
                "document_title": passage["topic"],
                "annotation_status": "assistant_draft_requires_human_review",
                "slots": [
                    {
                        "slot_id": sid,
                        "question": question,
                        "quote": None,
                        "kind": "modality"
                        if sid == "explicit_duty"
                        else "exception"
                        if sid == "allowed_exception"
                        else "condition",
                        "attaches_to": "exception" if sid == "exception_condition" else "duty",
                    }
                    for sid, question in PHILOSOPHY_QUESTIONS.items()
                ],
            }
        )
    prompts = yaml.safe_load((root / "prompts/generation_one.yaml").read_text(encoding="utf-8"))
    chains = []
    for source in sources:
        source.update(text_id="source:" + source["passage_id"], generation=0)
        for style, variants in prompts["styles"].items():
            if source["group"] != "statutory" and style != "paraphrase":
                continue
            for variant, instruction in variants.items():
                chains.append(
                    {
                        "chain_id": f"{source['passage_id']}:{style}:{variant}",
                        "passage_id": source["passage_id"],
                        "style": style,
                        "variant": variant,
                        "instruction": instruction,
                    }
                )
    return sources, chains


def reading_format(slots: list[dict]) -> dict:
    """Structured output constrains syntax; it does not establish semantic correctness."""
    row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "slot_id": {"type": "string", "enum": [s["slot_id"] for s in slots]},
            "status": {"type": "string", "enum": ["present", "absent", "uncertain"]},
            "quote": {"type": ["string", "null"]},
            "note": {"type": "string"},
        },
        "required": ["slot_id", "status", "quote", "note"],
    }
    # An Anthropic `output_config.format`. The nullable `quote` union was checked
    # against the live API in the model-selection probe before relying on it.
    return {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"slots": {"type": "array", "items": row}},
            "required": ["slots"],
        },
    }


def digest(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
