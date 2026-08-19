from __future__ import annotations

import re

import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag


def parse_las_html(html: str, document_id: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select("a.paragraf[name]")

    if not anchors:
        raise ValueError("LAS HTML contains no paragraph anchors")

    records = [
        _paragraph_record(anchor, document_id, order)
        for order, anchor in enumerate(anchors, start=1)
    ]
    records.extend(_transitional_records(soup, document_id, len(records) + 1))

    return pd.DataFrame(records)


def _paragraph_record(
    anchor: Tag, document_id: str, order: int
) -> dict[str, object]:
    source_anchor = str(anchor["name"])
    nodes = _provision_nodes(anchor)
    heading = anchor.find_previous("h4")
    text = _normalize_text(nodes)

    if not text:
        raise ValueError(f"LAS paragraph {source_anchor} contains no text")

    return {
        "document_id": document_id,
        "provision_suffix": source_anchor,
        "kind": "paragraph",
        "source_anchor": source_anchor,
        "label": anchor.get_text(" ", strip=True),
        "heading": heading.get_text(" ", strip=True) if heading else "",
        "order": order,
        "text": text,
        "subsection_anchors": _subsection_anchors(nodes),
        "amendment_notes": _amendment_notes(nodes),
    }


def _transitional_records(
    soup: BeautifulSoup, document_id: str, first_order: int
) -> list[dict[str, object]]:
    heading = soup.find("h3", attrs={"name": "overgang"})
    if heading is None:
        raise ValueError("LAS HTML contains no transitional-provisions heading")

    text = _normalize_text(list(heading.next_siblings))
    marker_pattern = re.compile(r"(?m)^(?P<sfs>\d{4}:\d+)$")
    markers = list(marker_pattern.finditer(text))
    if not markers:
        raise ValueError("LAS transitional provisions contain no SFS markers")

    records: list[dict[str, object]] = []
    for offset, marker in enumerate(markers):
        end = markers[offset + 1].start() if offset + 1 < len(markers) else len(text)
        sfs_number = marker.group("sfs")
        records.append(
            {
                "document_id": document_id,
                "provision_suffix": f"overgang:{sfs_number.replace(':', '-')}",
                "kind": "transitional_provision",
                "source_anchor": "overgang",
                "label": f"SFS {sfs_number}",
                "heading": "Övergångsbestämmelser",
                "order": first_order + offset,
                "text": text[marker.start() : end].strip(),
                "subsection_anchors": [],
                "amendment_notes": [],
            }
        )

    return records


def _provision_nodes(anchor: Tag) -> list[Tag | NavigableString]:
    nodes: list[Tag | NavigableString] = []
    for sibling in anchor.next_siblings:
        if isinstance(sibling, Tag):
            if sibling.name in {"h3", "h4"}:
                break
            if sibling.name == "a" and "paragraf" in sibling.get("class", []):
                break
        nodes.append(sibling)
    return nodes


def _normalize_text(nodes: list[Tag | NavigableString]) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, NavigableString):
            parts.append(str(node))
        elif node.name == "br":
            parts.append("\n")
        elif node.name == "p":
            parts.append("\n\n")
        else:
            parts.append(node.get_text(" ", strip=False))

    text = "".join(parts).replace("\u00a0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _subsection_anchors(nodes: list[Tag | NavigableString]) -> list[str]:
    anchors: list[str] = []
    for node in nodes:
        if not isinstance(node, Tag):
            continue
        candidates = [node] if node.name == "a" else node.select("a[name]")
        anchors.extend(
            str(candidate["name"])
            for candidate in candidates
            if re.fullmatch(r"P[^\s]+S\d+", str(candidate.get("name", "")))
        )
    return anchors


def _amendment_notes(nodes: list[Tag | NavigableString]) -> list[str]:
    notes: list[str] = []
    for node in nodes:
        if not isinstance(node, Tag):
            continue
        candidates = [node] if node.name == "i" else node.select("i")
        notes.extend(candidate.get_text(" ", strip=True) for candidate in candidates)
    return notes
