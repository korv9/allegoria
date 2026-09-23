"""A deterministic reader for IETF RFC requirements (RFC 2119 keywords).

RFCs state obligations with an explicit, machine-readable vocabulary: MUST,
SHOULD, MAY and their negatives. That makes the modality rung of every
requirement readable **without a model and without lexical guesswork** -- the
strongest fit for the engine. Reading MUST > SHOULD > MAY as binding > weak >
absent, a requirement that moves from MUST to SHOULD between two revisions of a
spec is a modality weakening on a duty: a loosening. `drift` signs that change
across two versions; `requirements` inventories one.

Pure standard library. The reflow/sentence split is a heuristic tuned for plain
RFC text; it is a reader, and like any reader its recall is a separate question
from the metric.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from meaningquality.direction import Modality, Part, SlotChange, classify

_KEYWORD = re.compile(
    r"\b(MUST NOT|MUST|SHALL NOT|SHALL|SHOULD NOT|SHOULD|NOT RECOMMENDED|RECOMMENDED|REQUIRED|MAY|OPTIONAL)\b"
)
_MODALITY = {
    "MUST": Modality.BINDING,
    "MUST NOT": Modality.BINDING,
    "REQUIRED": Modality.BINDING,
    "SHALL": Modality.BINDING,
    "SHALL NOT": Modality.BINDING,
    "SHOULD": Modality.WEAK,
    "SHOULD NOT": Modality.WEAK,
    "RECOMMENDED": Modality.WEAK,
    "NOT RECOMMENDED": Modality.WEAK,
    "MAY": Modality.ABSENT,
    "OPTIONAL": Modality.ABSENT,
}
_PAGE = re.compile(r"^(RFC \d+|Internet-Draft|\[Page \d+\]|[A-Z][\w.]+.*\[Page \d+\])", re.M)


@dataclass(frozen=True)
class Requirement:
    sentence: str
    keyword: str
    modality: Modality


def _reflow(text: str) -> list[str]:
    """RFC plain text into paragraphs: strip page headers/footers and form feeds,
    join wrapped lines within a blank-line-separated block, collapse whitespace."""
    text = text.replace("\x0c", "\n")
    lines = [ln for ln in text.splitlines() if not _PAGE.match(ln.strip())]
    blocks, cur = [], []
    for ln in lines:
        if ln.strip():
            cur.append(ln.strip())
        elif cur:
            blocks.append(" ".join(cur))
            cur = []
    if cur:
        blocks.append(" ".join(cur))
    return [re.sub(r"\s+", " ", b) for b in blocks]


def _sentences(block: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.:])\s+(?=[A-Z(])", block) if s.strip()]


def _is_boilerplate(sentence: str) -> bool:
    """The RFC 2119 notation section quotes the keywords rather than using them."""
    return sentence.count('"') >= 2 or "document are to be interpreted" in sentence


def requirements(text: str) -> list[Requirement]:
    """Every normative statement in one RFC, with its RFC 2119 keyword and rung."""
    out = []
    for block in _reflow(text):
        for sentence in _sentences(block):
            if _is_boilerplate(sentence):
                continue
            m = _KEYWORD.search(sentence)
            if m:
                kw = m.group(0)
                out.append(Requirement(sentence, kw, _MODALITY[kw]))
    return out


def profile(reqs: list[Requirement]) -> dict:
    """The requirement-strength profile of one spec: counts and shares by modality
    rung. A descriptive corpus-level view, distinct from the per-requirement sign:
    a successor with a smaller binding (MUST) share has loosened its overall
    posture even when no single requirement can be matched one-to-one."""
    total = len(reqs) or 1
    counts = {"binding": 0, "weak": 0, "absent": 0}
    for r in reqs:
        counts[r.modality.name.lower()] += 1
    shares = {k: round(100 * v / total, 1) for k, v in counts.items()}
    return {"requirements": len(reqs), "counts": counts, "shares_pct": shares}


def _key(sentence: str) -> str:
    """A version-stable key: the sentence with the keyword masked out, so the same
    requirement stated at a different strength across revisions matches."""
    return re.sub(_KEYWORD, "<RFC2119>", sentence).lower().strip()


def drift(old: list[Requirement], new: list[Requirement]) -> list[dict]:
    """Sign each requirement whose modality changed between two RFC versions.

    Matching is by the keyword-masked sentence, so MUST -> SHOULD on the same
    requirement is detected and signed as a modality change on a duty (loosening);
    SHOULD -> MUST tightens. Requirements only in one version are reported as
    added/removed, not signed here.
    """
    old_by = {_key(r.sentence): r for r in old}
    new_by = {_key(r.sentence): r for r in new}
    changes = []
    for key, nr in new_by.items():
        orq = old_by.get(key)
        if orq and orq.keyword != nr.keyword:
            change = SlotChange.modality(Part.DUTY, orq.modality, nr.modality)
            changes.append(
                {
                    "from_keyword": orq.keyword,
                    "to_keyword": nr.keyword,
                    "direction": classify(change).value,
                    "requirement": nr.sentence,
                }
            )
    return changes
