"""Emit the hand-labelled `om inte` gold set.

The labels below were assigned by reading all 80 sampled hits in context, before
any fix was written. This script only joins them to the sampled spans so the
gold file cannot drift from the sample through transcription.

    python scripts/write_om_inte_gold.py \
        --sample review/evidence/om_inte_sample.json \
        --out tests/fixtures/om_inte_gold.yaml

Re-running regenerates the file. Correcting a label means editing LABELS here
and committing the change with its reason -- never editing the YAML silently.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Grounds are syntactic, not impressionistic. The recurring ones:
COMPLEMENT = (
    "`om att` introduces a complement clause to the preceding noun or verb, not a condition"
)
PREP_RELATIVE = "`om` is a prepositional complement; `inte` sits inside a `som` relative clause"
PREP_MATRIX = (
    "`om` is a prepositional complement of the preceding noun; the negation belongs to the "
    "matrix verb, not to any conditional clause"
)
PREP_TITLE = "`om` is prepositional inside a statute title; `inte` negates the matrix verb"
COORD_INFINITIVE = "`inte` negates a coordinated infinitive in an enumeration, not a condition"
COND_BARE = (
    "`om` is the conditional subjunction and `inte` is the clause negation directly after it"
)
COND_SUBJECT = "`om` is the conditional subjunction; the gap is the subject NP of the same clause"
COND_COORD_SUBJECT = (
    "`om` is the conditional subjunction; the gap is a subject NP coordinated with `eller` "
    "inside the same clause"
)
COND_PRONOUN = (
    "`om` is the conditional subjunction; the gap is a pronoun subject of the same clause"
)
CONCESSIVE = (
    "`även om` concessive conditional: `om` and `inte` share one clause. Concessive rather than "
    "carve-out in force -- see the labelling policy note in the header"
)

# index (1-based, in the sample's own order) -> (label, grounds)
LABELS: dict[int, tuple[str, str]] = {
    1: ("spurious", PREP_RELATIVE),
    2: ("conditional", COND_COORD_SUBJECT),
    3: ("spurious", COMPLEMENT),
    4: ("spurious", COMPLEMENT),
    5: ("spurious", COMPLEMENT),
    6: ("spurious", COMPLEMENT),
    7: ("conditional", COND_COORD_SUBJECT),
    8: ("spurious", COMPLEMENT),
    9: ("spurious", COMPLEMENT),
    10: ("spurious", COORD_INFINITIVE),
    11: ("spurious", PREP_MATRIX),
    12: ("spurious", PREP_RELATIVE),
    13: ("conditional", COND_COORD_SUBJECT),
    14: ("spurious", COMPLEMENT),
    15: ("spurious", COMPLEMENT),
    16: ("spurious", PREP_RELATIVE),
    17: ("conditional", CONCESSIVE),
    18: ("spurious", COMPLEMENT),
    19: ("conditional", COND_BARE),
    20: ("conditional", COND_SUBJECT),
    21: ("spurious", PREP_RELATIVE),
    22: ("conditional", CONCESSIVE),
    23: ("conditional", COND_BARE),
    24: ("conditional", COND_BARE),
    25: ("conditional", COND_BARE),
    26: ("conditional", COND_BARE),
    27: ("conditional", COND_BARE),
    28: ("conditional", COND_BARE),
    29: ("spurious", PREP_MATRIX),
    30: ("conditional", COND_SUBJECT),
    31: ("conditional", COND_PRONOUN),
    32: ("conditional", COND_SUBJECT),
    33: ("conditional", COND_SUBJECT),
    34: ("conditional", COND_SUBJECT),
    35: ("conditional", COND_BARE),
    36: ("conditional", COND_SUBJECT),
    37: ("conditional", COND_PRONOUN),
    38: ("conditional", COND_SUBJECT),
    39: ("conditional", COND_PRONOUN),
    40: ("conditional", COND_SUBJECT),
    41: ("conditional", COND_BARE),
    42: ("conditional", COND_PRONOUN),
    43: ("conditional", COND_BARE),
    44: ("conditional", COND_SUBJECT),
    45: ("conditional", COND_BARE),
    46: ("conditional", COND_SUBJECT),
    47: ("conditional", COND_SUBJECT),
    48: ("conditional", COND_SUBJECT),
    49: ("conditional", COND_BARE),
    50: ("conditional", COND_BARE),
    51: ("conditional", COND_SUBJECT),
    52: ("conditional", COND_SUBJECT),
    53: ("conditional", COND_BARE),
    54: ("conditional", COND_PRONOUN),
    55: ("spurious", COMPLEMENT),
    56: ("conditional", COND_SUBJECT),
    57: ("spurious", PREP_TITLE),
    58: ("conditional", CONCESSIVE),
    59: ("conditional", COND_PRONOUN),
    60: ("conditional", COND_SUBJECT),
    61: ("conditional", COND_SUBJECT),
    62: ("conditional", COND_PRONOUN),
    63: ("conditional", COND_BARE),
    64: ("conditional", COND_BARE),
    65: ("conditional", COND_PRONOUN),
    66: ("conditional", COND_SUBJECT),
    67: ("conditional", COND_SUBJECT),
    68: ("conditional", COND_SUBJECT),
    69: ("conditional", COND_PRONOUN),
    70: ("spurious", COORD_INFINITIVE),
    71: ("conditional", COND_BARE),
    72: ("conditional", COND_SUBJECT),
    73: ("conditional", COND_SUBJECT),
    74: ("conditional", COND_PRONOUN),
    75: ("conditional", COND_PRONOUN),
    76: ("spurious", PREP_MATRIX),
    77: ("conditional", COND_BARE),
    78: ("conditional", COND_BARE),
    79: ("conditional", COND_BARE),
    80: ("spurious", PREP_MATRIX),
}

HEADER = """\
# Gold set for the `om inte` exception marker.
#
# 80 hits, hand-labelled in context BEFORE any fix was written, so the fix
# cannot be tuned to its own exam. Sampled by scripts/sample_om_inte.py from
# 2843 distinct hits across pools v1 and v2, seed 20260911.
#
# FROZEN. Do not edit this file to make a scorecard look better. A label that
# turns out to be wrong is corrected by changing LABELS in
# scripts/write_om_inte_gold.py and regenerating, in a commit that states the
# reason.
#
# Strata (deliberately enriched with hard cases):
#   known-defective-v1  18  every v1 hit whose span crosses a clause boundary
#   top-50-ranked       57  one seeded-random hit from each top-50 provision
#   random-seed-...      5  drawn from the remaining hits
#
# Because the set is enriched, precision measured on it is a LOWER BOUND on
# corpus-wide precision, not an estimate of it. Recall is measured over the
# conditional hits present here, which skew toward top-ranked provisions.
#
# Labels
#   conditional  `om` is the conditional subjunction and `inte` is the negation
#                of that same clause -- the phrase marks a real carve-out.
#   spurious     the span crosses out of the clause the `om` opened, so the
#                match is an artifact of the gap, not an exception marker.
#
# LABELLING POLICY, applied consistently and worth a decision:
# Four hits are concessive `även om ... inte` ("applies even if X does not").
# These are syntactically identical to a carve-out -- one `om` clause, one
# negation -- but pragmatically they EXTEND a rule rather than carve out of it.
# They are labelled `conditional` because the regex is a marker detector and
# DIRECTION.md assigns the carve-out judgment to hand annotation. Labelling them
# `spurious` would penalise a fix for something that is not the clause-crossing
# defect. Entries affected: see grounds mentioning "concessive".
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sample = json.loads(args.sample.read_text(encoding="utf-8"))
    hits = sample["hits"]
    if len(hits) != len(LABELS):
        raise SystemExit(f"sample has {len(hits)} hits but {len(LABELS)} labels are defined")

    lines = [
        HEADER,
        "",
        f"seed: {sample['seed']}",
        f"total_hits_in_corpus: {sample['total_hits']}",
        "hits:",
    ]
    for index, hit in enumerate(hits, start=1):
        label, grounds = LABELS[index]
        lines.append(f"  - index: {index}")
        lines.append(f"    provision_id: {_quote(hit['provision_id'])}")
        lines.append(f"    span: {_quote(hit['span'])}")
        lines.append(f"    char_offset: {hit['char_offset']}")
        lines.append(f"    pools: [{', '.join(hit['pools'])}]")
        lines.append(f"    selection_reason: {_quote(hit['selection_reason'])}")
        lines.append(f"    label: {label}")
        lines.append(f"    grounds: {_quote(grounds)}")
        lines.append(f"    context: {_quote(hit['context'].strip())}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    counts = {"conditional": 0, "spurious": 0}
    for label, _grounds in LABELS.values():
        counts[label] += 1
    print(
        f"GOLD SET | {len(hits)} hits | conditional {counts['conditional']}, "
        f"spurious {counts['spurious']} | {args.out}"
    )


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


if __name__ == "__main__":
    main()
