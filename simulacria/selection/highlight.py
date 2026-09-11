"""SELECTION. Render marker hits in place, so a match can be seen and not just counted.

Not measurement. This is presentation over `markers.iter_matches`; it computes
no matches of its own, so it cannot drift from what the pipeline actually does.

Reading that `om inte` fired tells you nothing about *where* or *on what*. The
`om inte` defect -- a gap crossing a clause boundary -- was invisible in a
marker list and obvious the moment the span was shown in its sentence.
"""

from __future__ import annotations

from html import escape
from itertools import pairwise

from simulacria.selection.markers import CLAUSE_BOUNDARY, MARKER_SETS, Marker, iter_matches

CATEGORY_COLOURS = {
    "duty": "#1b5e20",
    "exception": "#b71c1c",
    "qualifier": "#0d47a1",
}
CATEGORY_BACKGROUNDS = {
    "duty": "#e8f5e9",
    "exception": "#ffebee",
    "qualifier": "#e3f2fd",
}


def marker_spans(text: str) -> list[dict[str, object]]:
    """Every marker occurrence as (category, marker, span, start, end), in order.

    Overlaps are kept. Two markers legitimately match the same characters --
    `dock` and `ska inte` both fire on "ska dock inte" -- and hiding that would
    misrepresent the scoring, which counts both.
    """
    found: list[dict[str, object]] = []
    for category, markers in MARKER_SETS:
        for label, match in iter_matches(text, markers):
            found.append(
                {
                    "category": category,
                    "marker": label,
                    "span": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return sorted(found, key=lambda hit: (int(hit["start"]), -int(hit["end"])))


def _layered(text: str, spans: list[dict[str, object]]) -> list[tuple[int, int, list[dict]]]:
    """Split the text at every span boundary, carrying which spans cover each piece."""
    edges = sorted(
        {0, len(text)} | {int(s["start"]) for s in spans} | {int(s["end"]) for s in spans}
    )
    pieces: list[tuple[int, int, list[dict]]] = []
    for start, end in pairwise(edges):
        covering = [s for s in spans if int(s["start"]) <= start and int(s["end"]) >= end]
        pieces.append((start, end, covering))
    return pieces


def marker_html(text: str, categories: tuple[str, ...] = ("duty", "exception", "qualifier")) -> str:
    """The provision with every marker hit highlighted in place, colour-coded.

    Innermost-winning: where markers overlap, the piece takes the colour of the
    narrowest span covering it, and its tooltip lists every marker that covers
    it. Returns HTML for `IPython.display.HTML`.
    """
    spans = [hit for hit in marker_spans(text) if hit["category"] in categories]
    out: list[str] = []
    for start, end, covering in _layered(text, spans):
        piece = escape(text[start:end])
        if not covering:
            out.append(piece)
            continue
        narrowest = min(covering, key=lambda s: int(s["end"]) - int(s["start"]))
        category = str(narrowest["category"])
        tooltip = escape(", ".join(f"{s['category']}:{s['marker']}" for s in covering))
        out.append(
            f'<span title="{tooltip}" style="background:{CATEGORY_BACKGROUNDS[category]};'
            f"color:{CATEGORY_COLOURS[category]};border-bottom:2px solid "
            f'{CATEGORY_COLOURS[category]};padding:1px 0">{piece}</span>'
        )
    body = "".join(out).replace("\n", "<br>")
    return f'<div style="font-family:Georgia,serif;line-height:2;font-size:15px">{body}</div>'


def legend_html() -> str:
    """A colour key for `marker_html`, built from the same colour table."""
    chips = "".join(
        f'<span style="background:{CATEGORY_BACKGROUNDS[c]};color:{CATEGORY_COLOURS[c]};'
        f'border-bottom:2px solid {CATEGORY_COLOURS[c]};padding:2px 8px;margin-right:8px">{c}</span>'
        for c, _ in MARKER_SETS
    )
    return f'<div style="font-family:system-ui;font-size:13px">{chips}</div>'


def span_html(text: str, start: int, end: int, note: str = "") -> str:
    """One arbitrary span marked in its surrounding text.

    Used to show a single gold-set hit with its clause boundary, where the
    marker list is not the point -- the one span is.
    """
    before, middle, after = escape(text[:start]), escape(text[start:end]), escape(text[end:])
    label = f'<span style="color:#b71c1c;font-size:12px"> ← {escape(note)}</span>' if note else ""
    return (
        '<div style="font-family:Georgia,serif;line-height:2;font-size:15px">'
        f'{before}<span style="background:#ffebee;color:#b71c1c;border-bottom:2px solid #b71c1c">'
        f"{middle}</span>{after}{label}</div>"
    )


def clause_boundary_html(text: str, start: int, end: int) -> str:
    """A span with the clause-boundary tokens inside it called out.

    This is what makes a spurious `om inte` legible: the gap is not merely long,
    it has stepped over an `att` or a `som` and left the clause it opened.
    """
    inner = text[start:end]
    pieces: list[str] = []
    cursor = 0
    for match in CLAUSE_BOUNDARY.finditer(inner):
        pieces.append(escape(inner[cursor : match.start()]))
        pieces.append(
            '<span style="background:#ffd600;color:#000;font-weight:600;padding:0 2px">'
            f"{escape(match.group(0))}</span>"
        )
        cursor = match.end()
    pieces.append(escape(inner[cursor:]))
    marked = "".join(pieces)
    return (
        '<div style="font-family:Georgia,serif;line-height:2;font-size:15px">'
        f"{escape(text[:start])}"
        f'<span style="background:#ffebee;border-bottom:2px solid #b71c1c">{marked}</span>'
        f"{escape(text[end:])}</div>"
    )


__all__ = [
    "CATEGORY_BACKGROUNDS",
    "CATEGORY_COLOURS",
    "Marker",
    "clause_boundary_html",
    "legend_html",
    "marker_html",
    "marker_spans",
    "span_html",
]
