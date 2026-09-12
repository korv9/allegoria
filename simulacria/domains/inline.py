"""Corpora whose text is written in the corpus file itself.

The constructed philosophical passages are the case this exists for: there is no
upstream document to parse, so the corpus is the source. The text is still
hash-pinned, because a passage edited after a run was planned would silently
change what that run measured.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from simulacria.domains.base import Domain, PassageSource, register


def resolve(passage_id: str, _root: Path, spec: dict) -> PassageSource:
    text = spec.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"inline passage {passage_id} carries no text")
    expected = spec.get("text_sha256")
    if not expected:
        raise ValueError(f"inline passage {passage_id} must pin text_sha256")
    if sha256(text.encode("utf-8")).hexdigest() != expected:
        raise ValueError(f"inline passage {passage_id} does not match its pinned hash")
    return PassageSource(
        text=text,
        document_title=spec.get("topic") or spec.get("document_title") or passage_id,
        source_url=spec.get("source") or spec.get("source_url") or "inline corpus",
        source_sha256=None,
    )


DOMAIN = register(
    Domain(
        name="inline",
        language="any",
        id_format="any id unique within the corpus, e.g. categorical-01",
        resolve=resolve,
        notes="Text lives in the corpus file and is pinned by text_sha256.",
    )
)
