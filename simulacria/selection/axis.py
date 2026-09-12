"""Normative-axis selection audit. No slot extraction or direction inference."""

import json
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from statistics import mean, median, quantiles

import yaml

from simulacria.selection.highlight import marker_spans

GROUPS = ("virtue", "categorical", "conditional", "statutory")
CATEGORIES = ("duty", "exception", "qualifier")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_corpus(path: Path) -> list[dict]:
    """Read the shared passage envelope; reject corrupt identity and provenance."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 2:
        raise ValueError(f"{path}: unsupported corpus schema")
    rows = data.get("passages")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: passages must be a nonempty list")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError(f"{path}: invalid passage")
        for key in ("passage_id", "group", "topic", "text", "text_sha256", "source"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"{path}: missing {key}")
        if row["passage_id"] in seen:
            raise ValueError(f"{path}: duplicate passage_id {row['passage_id']}")
        seen.add(row["passage_id"])
        if row["group"] not in GROUPS:
            raise ValueError(f"{path}: unknown group {row['group']}")
        if sha256(row["text"].encode("utf-8")).hexdigest() != row["text_sha256"]:
            raise ValueError(f"{path}: text hash mismatch for {row['passage_id']}")
    return rows


def verify_statutory_snapshot(rows: list[dict], root: Path) -> list[dict]:
    """Verify derivative text against the sheet; carry the original manifest hash."""
    manifests = {}
    for name in ("manifest.json", "manifest_v2.json"):
        data = json.loads((root / "data/source/sfs" / name).read_text(encoding="utf-8"))
        for document in data["documents"]:
            manifests.setdefault(document["document_id"], document["raw_sha256"])
    verified = []
    sheets = {}
    for row in rows:
        source = (root / row["source"]).resolve()
        if not source.is_relative_to(root.resolve()):
            raise ValueError("specimen source outside project")
        if source not in sheets:
            raw = source.read_bytes()
            sheets[source] = (sha256(raw).hexdigest(), raw.decode("utf-8").replace("\r\n", "\n"))
        source_hash, sheet = sheets[source]
        if source_hash != row.get("source_sha256"):
            raise ValueError(f"specimen sheet hash mismatch: {source}")
        section = re.search(
            rf"## \d+\. {re.escape(row['passage_id'])}\n(.*?)(?=\n## \d+\.|\Z)",
            sheet,
            re.DOTALL,
        )
        if section is None:
            raise ValueError(f"missing specimen {row['passage_id']}")
        block = re.search(r"### Full text\s+```\n(.*?)\n```", section[1], re.DOTALL)
        if block is None or block[1] != row["text"]:
            raise ValueError(f"specimen text mismatch: {row['passage_id']}")
        if f"<{row['source_url']}>" not in section[1]:
            raise ValueError(f"specimen URL mismatch: {row['passage_id']}")
        document_id = row["passage_id"].split(":")[0]
        verified.append(
            {
                "passage_id": row["passage_id"],
                "sheet_text_verified": True,
                "document_source_sha256": manifests[document_id],
                "source_url": row["source_url"],
            }
        )
    return verified


def paired_lengths(rows: list[dict]) -> list[dict]:
    """Validate topic-matched controls and report character differences."""
    pairs = {}
    for row in rows:
        if row["group"] in ("categorical", "conditional"):
            key = row.get("pair_id")
            if not isinstance(key, str) or not key:
                raise ValueError("categorical/conditional passage missing pair_id")
            pair = pairs.setdefault(key, {})
            if row["group"] in pair:
                raise ValueError(f"duplicate member of pair {key}")
            pair[row["group"]] = row
    result = []
    for key, pair in sorted(pairs.items()):
        if set(pair) != {"categorical", "conditional"}:
            raise ValueError(f"incomplete pair {key}")
        a, b = pair["categorical"], pair["conditional"]
        if a["topic"] != b["topic"]:
            raise ValueError(f"topic mismatch in {key}")
        result.append(
            {
                "pair_id": key,
                "topic": a["topic"],
                "categorical": len(a["text"]),
                "conditional": len(b["text"]),
                "difference": len(b["text"]) - len(a["text"]),
            }
        )
    return result


def match_statutes(rows: list[dict], baseline: list[dict]) -> list[dict]:
    """Greedy nearest length without replacement, stable ID tie-break, no hit filter."""
    targets = sorted(
        (r for r in rows if r["group"] == "categorical"),
        key=lambda r: (len(r["text"]), r["passage_id"]),
    )
    remaining = list(baseline)
    if len(remaining) < len(targets):
        raise ValueError("not enough statutory specimens for matching")
    selected = []
    for target in targets:
        chosen = min(
            remaining, key=lambda r: (abs(len(r["text"]) - len(target["text"])), r["passage_id"])
        )
        remaining.remove(chosen)
        selected.append(
            {
                **chosen,
                "matched_to": target["passage_id"],
                "length_difference": len(chosen["text"]) - len(target["text"]),
            }
        )
    return selected


def passage_counts(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        counts = Counter(hit["category"] for hit in marker_spans(row["text"]))
        result.append(
            {
                "passage_id": row["passage_id"],
                "group": row["group"],
                "chars": len(row["text"]),
                **{c: counts[c] for c in CATEGORIES},
            }
        )
    return result


def hit_summary(rows: list[dict]) -> list[dict]:
    counts = passage_counts(rows)
    return [
        {
            "group": group,
            "passages": len(part),
            **{c: sum(r[c] for r in part) for c in CATEGORIES},
            **{f"passages_with_{c}": sum(r[c] > 0 for r in part) for c in CATEGORIES},
        }
        for group in GROUPS
        if (part := [r for r in counts if r["group"] == group])
    ]


def length_summary(rows: list[dict]) -> list[dict]:
    result = []
    for group in GROUPS:
        values = [len(r["text"]) for r in rows if r["group"] == group]
        if not values:
            continue
        quartiles = quantiles(values, method="inclusive") if len(values) > 1 else values * 3
        result.append(
            {
                "group": group,
                "n": len(values),
                "min": min(values),
                "q1": quartiles[0],
                "median": median(values),
                "q3": quartiles[2],
                "max": max(values),
                "mean": round(mean(values), 1),
            }
        )
    return result


def virtue_failures(rows: list[dict]) -> list[dict]:
    return [
        {**r, "hits": hits}
        for r in rows
        if r["group"] == "virtue" and (hits := marker_spans(r["text"]))
    ]


def expectation_checks(rows: list[dict]) -> list[dict]:
    """Report failed lexical predictions without suppressing or rejecting their data."""
    expected = {
        "virtue": (False, False, False),
        "categorical": (True, False, False),
        "conditional": (True, True, True),
        "statutory": (True, True, True),
    }
    return [
        {
            "passage_id": r["passage_id"],
            "group": r["group"],
            "expected": expected[r["group"]],
            "observed": tuple(r[c] > 0 for c in CATEGORIES),
            "pass": tuple(r[c] > 0 for c in CATEGORIES) == expected[r["group"]],
        }
        for r in passage_counts(rows)
    ]
