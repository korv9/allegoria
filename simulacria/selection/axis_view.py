"""Small HTML presentation for the source-only axis audit."""

from html import escape

from simulacria.selection.axis import passage_counts
from simulacria.selection.highlight import marker_html

LABELS = {
    "virtue": "Virtue description",
    "categorical": "Unconditional command",
    "conditional": "Conditional control",
    "statutory": "Statute",
}


def cards(rows: list[dict]) -> str:
    counts = {r["passage_id"]: r for r in passage_counts(rows)}
    blocks = []
    for row in rows:
        count = counts[row["passage_id"]]
        blocks.append(
            '<article style="flex:1;min-width:240px;padding:18px;border:1px solid #ccc;'
            'border-radius:8px;margin:5px">'
            f"<b>{LABELS[row['group']]}</b><p>{escape(row['passage_id'])} · "
            f"{count['chars']} characters</p>{marker_html(row['text'])}"
            f"<p>Hits: duty {count['duty']} · exception {count['exception']} · "
            f"qualifier {count['qualifier']}</p></article>"
        )
    return '<div style="display:flex;flex-wrap:wrap">' + "".join(blocks) + "</div>"
