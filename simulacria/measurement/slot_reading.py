"""Blind, quoted slot observations. No direction labels are requested or inferred.

The questions belong to the corpus, not to this module: a reading asks exactly
what the corpus file declares for that slot, in that corpus's language. Nothing
here knows which domain the text came from, which is what keeps a Swedish
statute and an English RFC readable by the same instrument.
"""

import json


def reading_format(slots: list[dict]) -> dict:
    """The JSON schema a reader must answer with. Syntax only, never correctness."""
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


def reading_input(text: str, slots: list[dict]) -> str:
    """Only current text and questions, no source quotes, parent, style or generation."""
    schema = [{"slot_id": s["slot_id"], "question": s["question"]} for s in slots]
    return json.dumps({"text": text, "schema": schema}, ensure_ascii=False)


def validate_reading(answer: str, text: str, slots: list[dict]) -> list[dict]:
    data = json.loads(answer)
    if not isinstance(data, dict) or set(data) != {"slots"}:
        raise ValueError("slot reading must contain only slots")
    rows = data["slots"]
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("slot reading must be a list of objects")
    ids = [r.get("slot_id") for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != {s["slot_id"] for s in slots}:
        raise ValueError("slot reading contains missing, duplicate or unknown slot IDs")
    for row in rows:
        if set(row) != {"slot_id", "status", "quote", "note"}:
            raise ValueError("unexpected slot reading fields")
        status, quote = row["status"], row["quote"]
        if status not in {"present", "absent", "uncertain"}:
            raise ValueError("unknown slot reading status")
        if not isinstance(row["note"], str) or not row["note"].strip():
            raise ValueError("slot reading requires a note")
        if status == "present" and (not isinstance(quote, str) or not quote.strip()):
            raise ValueError("present slot requires a nonempty quote")
        if status == "absent" and quote is not None:
            raise ValueError("absent slot cannot have a quote")
        if quote is not None and (
            not isinstance(quote, str) or not quote.strip() or quote not in text
        ):
            raise ValueError("slot evidence is not a verbatim substring")
    return rows
