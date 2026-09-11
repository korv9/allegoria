"""Blind, quoted slot observations. No direction labels are requested or inferred."""

import json

QUESTIONS = {
    "duty": "Finns en plikt att ta upp en tvist?",
    "scope": "Finns en avgränsning av vilka kostnader tvistprövningen avser?",
    "exception": "Finns ett undantag från den huvudsakliga regeln?",
    "exception_deadline": "Finns en tidsgräns för när en ansökan kan prövas?",
    "deadline_start": "Finns en händelse från vilken tidsgränsen för ansökan räknas?",
    "daily_rest": "Finns en bestämd varaktighet och beräkningsperiod för dygnsvila?",
    "temporary_exception": "Finns en möjlighet till tillfälligt avsteg från dygnsvilan?",
    "unforeseen_event": "Finns en beskrivning av vilka händelser som medger avsteg från dygnsvilan?",
    "compensation": "Finns ett krav på kompensation som villkor för avsteg från dygnsvilan?",
    "night_interval": "Finns ett klockslag eller intervall som nattvilan omfattar?",
    "night_exception": "Finns ett villkor för att arbete utförs under nattvilan?",
    "agreement": "Finns en avtalsanknuten avgränsning av semesterregeln?",
    "leave_period": "Finns en bestämd längd och förläggning för semesterperioden?",
    "special_reasons": "Finns ett villkor för att semesterperioden läggs till en annan tid?",
}


def reading_input(text: str, slots: list[dict]) -> str:
    """Only current text and questions, no source quotes, parent, style or generation."""
    schema = [
        {
            "slot_id": s["slot_id"],
            "question": s["question"] if "question" in s else QUESTIONS[s["slot_id"]],
        }
        for s in slots
    ]
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
