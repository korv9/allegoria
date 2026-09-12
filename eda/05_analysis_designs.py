# %% [markdown]
# # EDA 5 — which analyses this data can carry
#
# No model has been run, so this page contains no results about model behaviour
# and invents none. What it does is size the planned analyses against the data
# that exists: how many units each would have, what the unit even is, and which
# questions cannot be answered by running more chains.
#
# Everything is computed from the configs and corpora. No API calls.

# %%
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from IPython.display import display

from simulacria.generation.plan import load_config, plan
from simulacria.measurement.corpus import load_corpus

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 210)
pd.set_option("display.max_colwidth", 90)

configs = {
    path.stem: load_config(ROOT, path.relative_to(ROOT).as_posix())
    for path in sorted((ROOT / "configs").glob("*.yaml"))
}
plans = {name: plan(ROOT, config) for name, config in configs.items()}
for name, (sources, chains) in plans.items():
    depth = configs[name]["generations"]
    print(
        f"{name:<14} {len(sources):>3} passages  {len(chains):>3} chains  depth {depth:>2}  "
        f"{len(chains) * depth:>4} transformations"
    )

# %% [markdown]
# ## 1. The unit of analysis is not the reading
#
# A chain of ten generations produces ten readings, but they are not ten
# independent observations: generation 7 is built from generation 6. The
# independent unit is the **chain**, and everything inside it is correlated by
# construction.
#
# This is the number that governs every claim, and it is small.

# %%
units = []
for name, (sources, chains) in plans.items():
    depth = configs[name]["generations"]
    frame = pd.DataFrame(chains)
    units.append(
        {
            "experiment": name,
            "independent chains": len(chains),
            "passages": len(sources),
            "chains per passage": round(len(chains) / len(sources), 1),
            "styles": frame["style"].nunique(),
            "readings (correlated)": len(chains) * depth + len(sources),
            "readings per chain": depth,
        }
    )
display(pd.DataFrame(units))
print(
    "Reading count is what you pay for. Chain count is what you can reason from.\n"
    "Reporting the first as if it were the second is the easiest mistake here."
)

# %% [markdown]
# ## 2. The ordering test: how many slot pairs could ever resolve?
#
# The founding hypothesis is that the condition on an exception disappears
# before the exception itself. A chain can only contribute evidence if the
# passage carries both an exception slot and a condition attached to it.

# %%
pairs = []
for name, config in configs.items():
    for entry in config["corpora"]:
        for passage in load_corpus(ROOT / entry["path"], ROOT):
            exceptions = [s for s in passage["slots"] if s["kind"] == "exception"]
            conditions = [
                s
                for s in passage["slots"]
                if s["attaches_to"] == "exception" and s["kind"] != "exception"
            ]
            chains_here = [c for c in plans[name][1] if c["passage_id"] == passage["passage_id"]]
            pairs.append(
                {
                    "experiment": name,
                    "passage_id": passage["passage_id"],
                    "exception slots": len(exceptions),
                    "conditions on exception": len(conditions),
                    "pairs": len(exceptions) * len(conditions),
                    "chains": len(chains_here),
                    "pair-chains": len(exceptions) * len(conditions) * len(chains_here),
                }
            )
pairs = pd.DataFrame(pairs)
display(pairs[pairs.pairs > 0])
totals = pairs.groupby("experiment")[["pairs", "pair-chains"]].sum()
display(totals)
print(
    "A `pair-chain` is one condition/exception pair followed through one chain --\n"
    "the most granular thing the ordering test can observe, and still not\n"
    "independent of the other pairs in the same chain."
)

# %% [markdown]
# ## 3. What a "loosening" claim would need
#
# Direction is not implemented, and `DIRECTION.md` has two unresolved cases. But
# the slots that would carry a direction signal can be counted now: only slots
# whose disappearance has an agreed sign are usable.

# %%
rows = []
for entry_name, config in configs.items():
    for entry in config["corpora"]:
        for passage in load_corpus(ROOT / entry["path"], ROOT):
            for slot in passage["slots"]:
                rows.append(
                    {
                        "experiment": entry_name,
                        "domain": passage["domain"],
                        "kind": slot["kind"],
                        "attaches_to": slot["attaches_to"],
                        "direction_if_lost": (
                            "loosens"
                            if slot["attaches_to"] == "duty"
                            and slot["kind"] in {"condition", "deadline", "modality"}
                            else "tightens"
                            if slot["attaches_to"] == "exception"
                            else "unclear"
                        ),
                    }
                )
slot_directions = pd.DataFrame(rows).drop_duplicates()
display(pd.crosstab(slot_directions.domain, slot_directions.direction_if_lost))
print(
    "The labels above follow the plain reading of DIRECTION.md: losing a limit on\n"
    "a duty widens what is permitted, losing a limit on an exception narrows it.\n"
    "They are NOT the implemented metric, and case 9 and the ceiling question are\n"
    "exactly the cases where this plain reading is known to be contested."
)

# %% [markdown]
# ## 4. Analyses ranked by what they need
#
# Honest ordering: what can be computed the moment one run exists, what needs
# human review first, and what needs a decision no amount of data supplies.

# %%
display(
    pd.DataFrame(
        [
            {
                "analysis": "Survival of each slot by generation",
                "unit": "chain",
                "needs": "one completed run",
                "blocked by": "-",
                "reportable as": "share read present, with gaps shown as gaps",
            },
            {
                "analysis": "Literal quote loss by generation",
                "unit": "chain",
                "needs": "one completed run",
                "blocked by": "-",
                "reportable as": "verbatim match rate; not semantic absence",
            },
            {
                "analysis": "Style comparison (paraphrase vs allegorize)",
                "unit": "chain",
                "needs": "one completed run",
                "blocked by": "8 chains per passage, 3 passages",
                "reportable as": "descriptive only",
            },
            {
                "analysis": "Condition-before-exception ordering",
                "unit": "pair-chain",
                "needs": "completed chains where both slots start present",
                "blocked by": "spatial-order confounder (EDA 4, section 4)",
                "reportable as": "counts per ordering category",
            },
            {
                "analysis": "Loosening vs tightening",
                "unit": "slot transition",
                "needs": "direction metric",
                "blocked by": "DIRECTION.md case 9 and the ceiling proposal",
                "reportable as": "nothing yet",
            },
            {
                "analysis": "Reader reliability",
                "unit": "slot reading",
                "needs": "blind human review of the same texts",
                "blocked by": "no human review exists",
                "reportable as": "agreement rate, once it exists",
            },
            {
                "analysis": "Cross-domain comparison (sv vs en)",
                "unit": "experiment",
                "needs": "runs in both domains",
                "blocked by": "language, register and corpus differ at once",
                "reportable as": "side by side, never pooled",
            },
        ]
    )
)

# %% [markdown]
# ## 5. Confounders already visible in the data
#
# Each of these was measured in an earlier EDA page, before any model ran.

# %%
display(
    pd.DataFrame(
        [
            {
                "confounder": "Passage length",
                "seen in": "EDA 2 section 4, EDA 3 section 2",
                "effect": "drives marker counts (rho 0.73); much weaker inside the shortlist (rho 0.20)",
                "handling": "compare within length bands; report passage length with any result",
            },
            {
                "confounder": "Condition follows its exception in the text",
                "seen in": "EDA 4 section 4",
                "effect": "any truncation removes conditions first, for a trivial reason",
                "handling": "report text length per generation; treat truncated chains separately",
            },
            {
                "confounder": "Style is not one treatment",
                "seen in": "prompts/sv/transform.yaml",
                "effect": "variants a and b are different instructions, not repetitions",
                "handling": "never average a and b as replicates",
            },
            {
                "confounder": "Reader is weak",
                "seen in": "predictions/2026-09-11-amendment-cheapest-models.md",
                "effect": "3 of 9 readings invalid; the one known shift was missed",
                "handling": "treat 'present everywhere' as a possible instrument failure",
            },
            {
                "confounder": "Draft annotations",
                "seen in": "every corpus file",
                "effect": "slot set and attachment are unreviewed",
                "handling": "state it on every figure; review before publishing a number",
            },
        ]
    )
)

# %% [markdown]
# ## 6. The smallest useful next run
#
# Three statutory passages, eight chains each, ten generations: 240
# transformations and 243 readings. Enough to see whether the mechanism shows up
# at all, cheap enough to throw away, and small enough that nobody can mistake it
# for a study. Sizes and cost come from `scripts/run/chains.py --check`.

# %%
sources, chains = plans["allegoria-sv"]
statutory = [
    c
    for c in chains
    if any(s["passage_id"] == c["passage_id"] and s["group"] == "statutory" for s in sources)
]
depth = configs["allegoria-sv"]["generations"]
display(
    pd.DataFrame(
        [
            {
                "scope": "statutory group only",
                "chains": len(statutory),
                "transformations": len(statutory) * depth,
                "readings": len(statutory) * depth + 3,
                "command": "python scripts/run/chains.py --group statutory",
            },
            {
                "scope": "full Swedish experiment",
                "chains": len(chains),
                "transformations": len(chains) * depth,
                "readings": len(chains) * depth + len(sources),
                "command": "python scripts/run/chains.py",
            },
            {
                "scope": "English RFC domain",
                "chains": len(plans["rfc-en"][1]),
                "transformations": len(plans["rfc-en"][1]) * configs["rfc-en"]["generations"],
                "readings": len(plans["rfc-en"][1]) * configs["rfc-en"]["generations"] + 3,
                "command": "python scripts/run/chains.py --config configs/rfc-en.yaml",
            },
        ]
    )
)
