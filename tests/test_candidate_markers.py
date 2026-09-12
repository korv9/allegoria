"""Regression guard for the candidate-selection markers.

`tests/fixtures/must_surface.yaml` pins provisions that must keep surfacing.
The point is not that the heuristic is good -- it is that a change to the marker
sets did not silently drop material. The `\\bskal?l\\b` bug was caught only
because someone noticed a known provision had gone missing.

The provisions are parsed from the committed Bronze JSON, not from
`data/local/provisions.jsonl`, so this runs on a fresh clone with no build step.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

from simulacria.pipeline.silver import BRONZE_DIR, build_provisions
from simulacria.selection.shortlist import shortlist

FIXTURE = Path(__file__).parent / "fixtures/must_surface.yaml"
CATEGORIES = ("duty", "exception", "qualifier")


@lru_cache(maxsize=1)
def _candidates_by_id() -> dict[str, dict[str, object]]:
    provisions, _unparsable = build_provisions(BRONZE_DIR)
    candidates = shortlist(provisions)
    return {
        str(candidate["provision_id"]): {**candidate, "rank": rank}
        for rank, candidate in enumerate(candidates, start=1)
    }


def _fixture_entries() -> list[dict[str, object]]:
    entries = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["provisions"]
    assert 8 <= len(entries) <= 12, f"fixture holds {len(entries)} entries, expected 8-12"
    return entries


def test_fixture_provisions_still_surface() -> None:
    """Every pinned provision must still appear in the shortlist."""
    candidates = _candidates_by_id()
    dropped = [
        str(entry["provision_id"])
        for entry in _fixture_entries()
        if str(entry["provision_id"]) not in candidates
    ]

    assert not dropped, (
        f"{len(dropped)} pinned provision(s) no longer surface as candidates:\n  "
        + "\n  ".join(dropped)
        + "\nA marker pattern stopped matching. See tests/fixtures/must_surface.yaml "
        "for why each was pinned; update the fixture only if the loss was intended."
    )


def test_fixture_provisions_hit_their_markers() -> None:
    """Each pinned provision must still hit the markers it was chosen for."""
    candidates = _candidates_by_id()
    losses: list[str] = []

    for entry in _fixture_entries():
        provision_id = str(entry["provision_id"])
        candidate = candidates.get(provision_id)
        if candidate is None:
            losses.append(f"{provision_id}: dropped out of the shortlist entirely")
            continue

        for category in CATEGORIES:
            expected = set(entry.get(category) or [])
            actual = set(candidate[f"{category}_markers"])
            if missing := sorted(expected - actual):
                losses.append(
                    f"{provision_id}: {category} lost {missing} (still hits {sorted(actual)})"
                )

        if entry["determinacy"] != candidate["determinacy"]:
            losses.append(
                f"{provision_id}: determinacy went "
                f"{entry['determinacy']} -> {candidate['determinacy']}"
            )

    assert not losses, "Marker coverage regressed:\n  " + "\n  ".join(losses)


def test_worked_example_is_pinned() -> None:
    """The DIRECTION.md example must never be dropped from the fixture itself."""
    pinned = {str(entry["provision_id"]) for entry in _fixture_entries()}
    assert "sfs-2026-1281:K10P10" in pinned, (
        "sfs-2026-1281:K10P10 is the worked example DIRECTION.md is built around "
        "and must stay pinned"
    )
