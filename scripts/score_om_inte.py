"""Score `om inte` patterns against the frozen gold set.

    python scripts/score_om_inte.py
    python scripts/score_om_inte.py --show-changes current allowlist

A pattern "fires" on a gold entry when one of its matches starts at the same
offset as the labelled span. Every pattern here anchors on `om`, so that test is
unambiguous.

    fires + conditional -> true positive
    fires + spurious    -> false positive
    silent + conditional-> false negative
    silent + spurious   -> true negative

STRUCTURAL LIMIT, stated so the numbers are not over-read: the gold set was
sampled from the CURRENT pattern's own hits. A genuine carve-out the current
pattern never matched cannot appear in it. So this measures precision gains and
recall LOSSES against today's behaviour; it cannot measure recall gains, and the
current pattern scores recall 1.0 by construction, not by merit.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

import yaml

from simulacria.selection.markers import EXCEPTION_MARKERS
from simulacria.selection.pools import POOLS, PROJECT_ROOT, load_provisions
from simulacria.selection.shortlist import shortlist

GOLD = PROJECT_ROOT / "tests" / "fixtures" / "om_inte_gold.yaml"

CURRENT = next(pattern for label, pattern, _w in EXCEPTION_MARKERS if label == "om inte")

# Exactly the allowlist specified for the fix: a closed class of pronouns and
# determiners. `att` is absent, so `om att ...` cannot fire; `som`, `men`, `och`
# and `eller` are absent, so the gap cannot span them; no comma can appear
# because only listed word tokens may.
ALLOWLIST_TOKENS = "något annat|denna|detta|dessa|sådant|någon|annat|det|den|de|han|hon|hen|man"
ALLOWLIST = re.compile(rf"\bom\s+(?:(?:{ALLOWLIST_TOKENS})\s+){{0,3}}inte\b", re.IGNORECASE)

# The same allowlist widened with the determiners and quantifiers the gold set
# actually shows in subject position. Designed AFTER reading the labels, so it
# is a proposal to be judged, not an independent result.
WIDENED_TOKENS = (
    "något annat|någon sådan|sådana|sådant|sådan|denna|detta|dessa|någon|något|annat|andra"
    "|det|den|de|han|hon|hen|man|hans|hennes|dess"
)
WIDENED = re.compile(rf"\bom\s+(?:(?:{WIDENED_TOKENS})\s+){{0,3}}inte\b", re.IGNORECASE)

# A different shape: keep a gap, but temper it so it can never cross the tokens
# that end a clause. Not an allowlist -- it admits any token that is not a
# boundary marker, which is why it needs a decision rather than a merge.
BOUNDARY = "att|som|men|och|eller|vilket|där|när|då"
TEMPERED = re.compile(
    rf"\bom\s+(?:(?!(?:{BOUNDARY})\b)[^\s,;:.!?]+\s+){{0,3}}inte\b", re.IGNORECASE
)

# `eller` and `och` coordinate constituents INSIDE a clause; they do not end one
# the way `att`, `som` and `men` do. The gold set shows four genuine carve-outs
# with coordinated subjects ("om vapnet eller vapendelen inte"), so treating them
# as boundaries costs recall for no precision the other tokens do not already
# buy. Designed after reading the labels -- a proposal, not an independent result.
COORD_BOUNDARY = "att|som|men|vilket|där|när|då"
TEMPERED_COORD = re.compile(
    rf"\bom\s+(?:(?!(?:{COORD_BOUNDARY})\b)[^\s,;:.!?]+\s+){{0,4}}inte\b", re.IGNORECASE
)

PATTERNS = {
    "current": CURRENT,
    "allowlist": ALLOWLIST,
    "widened": WIDENED,
    "tempered": TEMPERED,
    "tempered_coord": TEMPERED_COORD,
}


@dataclass
class Scorecard:
    name: str
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0

    @property
    def precision(self) -> float:
        fired = self.true_positive + self.false_positive
        return self.true_positive / fired if fired else 0.0

    @property
    def recall(self) -> float:
        actual = self.true_positive + self.false_negative
        return self.true_positive / actual if actual else 0.0

    @property
    def f1(self) -> float:
        total = self.precision + self.recall
        return 2 * self.precision * self.recall / total if total else 0.0


def provision_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for pool in ("v2", "v1"):  # v1 last so its text wins where both exist
        for provision in load_provisions(POOLS[pool].output_path):
            texts[str(provision["provision_id"])] = str(provision["text"])
    return texts


def fires(pattern: re.Pattern[str], text: str, offset: int) -> bool:
    return any(match.start() == offset for match in pattern.finditer(text))


def score(name: str, pattern: re.Pattern[str], gold: list[dict], texts: dict[str, str]):
    card = Scorecard(name)
    decisions: dict[int, bool] = {}

    for entry in gold:
        text = texts[entry["provision_id"]]
        offset = int(entry["char_offset"])
        # PROTOCOL.md verbatim discipline: the labelled span must still be the
        # text at its recorded offset, or the gold set no longer describes it.
        span = entry["span"]
        if text[offset : offset + len(span)] != span:
            raise SystemExit(
                f"gold entry {entry['index']} no longer matches its provision text at offset {offset}"
            )

        fired = fires(pattern, text, offset)
        decisions[int(entry["index"])] = fired
        conditional = entry["label"] == "conditional"
        if fired and conditional:
            card.true_positive += 1
        elif fired:
            card.false_positive += 1
        elif conditional:
            card.false_negative += 1
        else:
            card.true_negative += 1

    return card, decisions


def project(pattern_name: str) -> None:
    """Report what swapping in a pattern would do, without shipping it.

    Nothing is written. A marker proposal is passed explicitly to the library;
    production marker state remains unchanged even when the comparison fails.
    """
    replacement = [
        (label, PATTERNS[pattern_name] if label == "om inte" else pattern, weight)
        for label, pattern, weight in EXCEPTION_MARKERS
    ]

    print(f"\nProjected effect of '{pattern_name}' on the candidate set (not shipped):")
    for pool in ("v1", "v2"):
        provisions = load_provisions(POOLS[pool].output_path)
        before = {str(c["provision_id"]): c for c in shortlist(provisions)}
        after = {
            str(c["provision_id"]): c for c in shortlist(provisions, exception_markers=replacement)
        }

        leaving = sorted(set(before) - set(after))
        specific_before = sum(1 for c in before.values() if c["determinacy"] == "specific")
        specific_after = sum(1 for c in after.values() if c["determinacy"] == "specific")
        print(
            f"  {pool}: candidates {len(before)} -> {len(after)} ({len(leaving)} leave), "
            f"specific {specific_before} -> {specific_after}"
        )
        for provision_id in leaving[:8]:
            print(f"      leaves: {provision_id}")
        if len(leaving) > 8:
            print(f"      ... {len(leaving) - 8} more")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patterns", nargs="*", default=list(PATTERNS))
    parser.add_argument("--show-changes", nargs=2, metavar=("FROM", "TO"))
    parser.add_argument("--project", help="report the candidate-set effect of this pattern")
    args = parser.parse_args()

    gold = yaml.safe_load(GOLD.read_text(encoding="utf-8"))["hits"]
    texts = provision_texts()

    cards: dict[str, Scorecard] = {}
    all_decisions: dict[str, dict[int, bool]] = {}
    for name in args.patterns:
        card, decisions = score(name, PATTERNS[name], gold, texts)
        cards[name] = card
        all_decisions[name] = decisions

    header = f"{'pattern':<12}{'TP':>5}{'FP':>5}{'FN':>5}{'TN':>5}{'precision':>12}{'recall':>9}{'F1':>8}"
    print(header)
    print("-" * len(header))
    for name, card in cards.items():
        print(
            f"{name:<12}{card.true_positive:>5}{card.false_positive:>5}"
            f"{card.false_negative:>5}{card.true_negative:>5}"
            f"{card.precision:>11.1%}{card.recall:>9.1%}{card.f1:>8.3f}"
        )

    if args.show_changes:
        source, target = args.show_changes
        by_index = {int(entry["index"]): entry for entry in gold}
        print(f"\nEntries whose classification changed, {source} -> {target}:")
        for index in sorted(by_index):
            before, after = all_decisions[source][index], all_decisions[target][index]
            if before == after:
                continue
            entry = by_index[index]
            movement = "now silent" if before else "now fires"
            verdict = "GOOD" if (after == (entry["label"] == "conditional")) else "COST"
            print(
                f"  [{verdict}] {index:>3} {entry['provision_id']:<34} "
                f"{entry['label']:<12} {movement}  span={entry['span']!r}"
            )

    if args.project:
        project(args.project)


if __name__ == "__main__":
    main()
