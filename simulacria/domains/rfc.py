"""IETF RFCs in plain text: the English test of whether this pipeline travels.

RFCs were chosen as the second domain because their normative language is
explicit and conventionalised -- MUST, MUST NOT, SHOULD, MAY, and exceptions
written as "unless" or "except" -- so duty, exception and condition slots mean
the same thing here as in a statute, in another language and another register.

A passage is one numbered section, addressed as `rfc-<number>:<section>`, for
example `rfc-2119:4`. Section text is cut out of the plain-text RFC by its
numbered heading; the bytes fetched from rfc-editor.org are what the bronze
envelope pins, exactly as with statute XML.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from simulacria.domains.base import Domain, PassageSource, register

SOURCE_DIR = "data/source/rfc"
BRONZE_DIR = "data/bronze/rfc"

# A heading starts at column 0 with a dotted section number: "4.  Terminology".
HEADING = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\.?\s+(?P<title>\S.*)$")
# Page furniture in the classic plain-text layout: a form feed, the footer that
# precedes it and the running header that follows. None of it is section text,
# and leaving it in would put a page header inside a quoted slot.
FOOTER = re.compile(r"^\S.*\[Page \d+\]\s*$")
HEADER = re.compile(r"^RFC\s+\d+\s+\S.*\b(19|20)\d{2}\s*$")
BLANK_RUN = re.compile(r"\n{3,}")


def sections(text: str) -> dict[str, dict[str, str]]:
    """Split a plain-text RFC into its numbered sections, in document order."""
    found: dict[str, dict[str, str]] = {}
    number: str | None = None
    title = ""
    body: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("\f") or FOOTER.match(line) or HEADER.match(line):
            continue
        heading = HEADING.match(line)
        if heading:
            if number is not None:
                found[number] = {"title": title, "text": "\n".join(body).strip()}
            number = heading["number"]
            title = heading["title"].strip()
            # The heading line stays in the body: in many RFCs it carries the
            # section's first sentence, and a passage must not start mid-thought.
            body = [line]
        elif number is not None:
            body.append(line)
    if number is not None:
        found[number] = {"title": title, "text": "\n".join(body).strip()}
    return found


def resolve(passage_id: str, root: Path, _spec: dict) -> PassageSource:
    document_id, _, section = passage_id.partition(":")
    if not section or not re.fullmatch(r"rfc-\d+", document_id):
        raise ValueError(f"invalid RFC passage id: {passage_id}")
    bronze_path = root / BRONZE_DIR / f"{document_id}.json"
    if not bronze_path.is_file():
        raise ValueError(f"{bronze_path} is missing; run scripts/pipeline/ingest_rfc.py first")
    bronze = json.loads(bronze_path.read_text(encoding="utf-8"))
    raw = (root / SOURCE_DIR / f"{document_id}.txt").read_bytes()
    if sha256(raw).hexdigest() != bronze["source_sha256"]:
        raise ValueError(f"source hash mismatch: {passage_id}")
    if bronze["text"] != raw.decode("utf-8"):
        raise ValueError(f"bronze payload mismatch: {passage_id}")
    if bronze["document_id"] != document_id:
        raise ValueError(f"bronze document mismatch: {passage_id}")
    found = sections(bronze["text"])
    if section not in found:
        raise ValueError(f"{document_id} has no section {section}")
    body = found[section]["text"]
    if not body.strip():
        raise ValueError(f"{passage_id} resolves to an empty section")
    return PassageSource(
        text=body,
        document_title=f"{bronze['title']} section {section}: {found[section]['title']}",
        source_url=f"{bronze['source_page_url']}#section-{section}",
        source_sha256=bronze["source_sha256"],
    )


DOMAIN = register(
    Domain(
        name="rfc",
        language="en",
        id_format="rfc-<number>:<section>, e.g. rfc-2119:4",
        resolve=resolve,
        source_dir=SOURCE_DIR,
        bronze_dir=BRONZE_DIR,
        notes="Plain-text RFC; sections are cut by numbered heading, bytes are hash-pinned.",
    )
)
