# %% [markdown]
# # EDA 4 — the annotated slots, across three domains
#
# The slots are what the experiment actually measures: a question, an attachment
# and a verbatim quote from the passage. This page compares them across Swedish
# statute, the constructed philosophical controls and the English RFC sections,
# straight from the corpus files. No API calls.
#
# **Every annotation here is an assistant draft with no human review.** That is
# the single largest caveat on anything downstream, and it applies to every count
# on this page.

# %%
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

from simulacria.measurement.corpus import load_corpus

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 210)
pd.set_option("display.max_colwidth", 70)

CORPORA = ["corpus/law_probe_v1.yaml", "corpus/philosophy_v1.yaml", "corpus/rfc_probe_v1.yaml"]
passages = [row for name in CORPORA for row in load_corpus(ROOT / name, ROOT)]

slots = pd.DataFrame(
    [
        {
            "domain": passage["domain"],
            "group": passage["group"],
            "passage_id": passage["passage_id"],
            "passage_chars": len(passage["text"]),
            "slot_id": slot["slot_id"],
            "kind": slot["kind"],
            "attaches_to": slot["attaches_to"],
            "question_chars": len(slot["question"]),
            "quote": slot["quote"],
            "quote_chars": len(slot["quote"]) if slot["quote"] else 0,
            "quote_start": passage["text"].find(slot["quote"]) if slot["quote"] else -1,
        }
        for passage in passages
        for slot in passage["slots"]
    ]
)
print(f"{len(passages)} passages, {len(slots)} slots, {slots.domain.nunique()} domains")

# %% [markdown]
# ## 1. Shape of each corpus

# %%
display(
    slots.groupby(["domain", "group"])
    .agg(
        passages=("passage_id", "nunique"),
        slots=("slot_id", "size"),
        slots_per_passage=("passage_id", lambda s: round(len(s) / s.nunique(), 1)),
        anchored_quotes=("quote", lambda s: int(s.notna().sum())),
        median_passage_chars=("passage_chars", "median"),
    )
    .reset_index()
)

# %% [markdown]
# ## 2. What kinds of slot exist, and what they attach to
#
# `attaches_to` is the field that decides the sign of a direction change: a
# condition on a *duty* and a condition on an *exception* move the norm opposite
# ways when they disappear. The distribution below is therefore not cosmetic.

# %%
display(pd.crosstab(slots.kind, slots.attaches_to, margins=True))
display(pd.crosstab(slots.domain, slots.kind))
display(pd.crosstab(slots.domain, slots.attaches_to))

# %% [markdown]
# ## 3. How much of a passage is actually anchored?
#
# Quotes are the evidence a reading must reproduce. If they cover a tiny fraction
# of the text, most of a rewrite is unmeasured; if they cover nearly all of it,
# the slots are not selecting anything in particular.

# %%
coverage = []
for passage in passages:
    text = passage["text"]
    covered = set()
    for slot in passage["slots"]:
        if not slot["quote"]:
            continue
        start = text.find(slot["quote"])
        covered.update(range(start, start + len(slot["quote"])))
    coverage.append(
        {
            "domain": passage["domain"],
            "passage_id": passage["passage_id"],
            "chars": len(text),
            "covered_chars": len(covered),
            "coverage": round(len(covered) / len(text), 3),
            "slots": len(passage["slots"]),
        }
    )
coverage = pd.DataFrame(coverage)
display(coverage.groupby("domain").coverage.describe()[["count", "min", "50%", "max"]].round(3))
display(coverage.sort_values("coverage").head(5))
display(coverage.sort_values("coverage", ascending=False).head(5))

fig, ax = plt.subplots(figsize=(9, 3.5))
for domain, group in coverage.groupby("domain"):
    ax.scatter(group.chars, group.coverage, label=domain, alpha=0.7)
ax.set(
    xlabel="passage characters",
    ylabel="share of characters inside a quote",
    title="Quote coverage by passage",
)
ax.legend()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4. Where in the passage does each element sit?
#
# The hypothesis under test is about *order in time* — does the condition on an
# exception disappear before the exception itself. This is the order in *space*,
# in the source text, which is a different thing and worth knowing first: if the
# condition almost always trails its exception, then anything that truncates a
# text will remove conditions first for a trivial reason.

# %%
anchored = slots[slots.quote_start >= 0].copy()
anchored["relative_position"] = (anchored.quote_start / anchored.passage_chars).round(3)
display(
    anchored.groupby(["domain", "attaches_to"])
    .relative_position.agg(["count", "mean", "median"])
    .round(3)
)

pairs = []
for passage in passages:
    text = passage["text"]
    exceptions = [s for s in passage["slots"] if s["kind"] == "exception" and s["quote"]]
    conditions = [
        s
        for s in passage["slots"]
        if s["attaches_to"] == "exception" and s["kind"] != "exception" and s["quote"]
    ]
    for exception in exceptions:
        for condition in conditions:
            pairs.append(
                {
                    "domain": passage["domain"],
                    "passage_id": passage["passage_id"],
                    "exception": exception["slot_id"],
                    "condition": condition["slot_id"],
                    "condition_after_exception": text.find(condition["quote"])
                    > text.find(exception["quote"]),
                }
            )
pairs = pd.DataFrame(pairs)
if len(pairs):
    display(pairs)
    print(
        f"{pairs.condition_after_exception.sum()} of {len(pairs)} condition-on-exception pairs "
        "have the condition standing after its exception in the source text."
    )
else:
    print("No condition-on-exception pairs are annotated in these corpora.")

# %% [markdown]
# ## 5. Quote length — what a reader has to reproduce verbatim
#
# A reading is rejected when its quote is not a verbatim span. Long quotes are
# harder to reproduce exactly after a rewrite, so quote length partly determines
# how often a slot can be confirmed at all.

# %%
display(anchored.groupby("domain").quote_chars.describe()[["count", "min", "50%", "max"]].round(1))
display(
    anchored.nlargest(5, "quote_chars")[["domain", "passage_id", "slot_id", "quote_chars", "quote"]]
)
print(
    "A quote spanning a line break (the RFC corpus) must be reproduced with its\n"
    "wrapping intact, which is why those spans are stored exactly as they wrap."
)

# %% [markdown]
# ## 6. Questions, in the corpus's own language
#
# Questions live in the corpus file, not in Python, so a corpus can be read in
# its own language. These are the exact strings a reader model is shown.

# %%
for domain in sorted(slots.domain.unique()):
    sample = slots[slots.domain == domain].drop_duplicates("slot_id").head(3)
    print(f"\n--- {domain} ---")
    for _, row in sample.iterrows():
        passage = next(p for p in passages if p["passage_id"] == row.passage_id)
        question = next(s["question"] for s in passage["slots"] if s["slot_id"] == row.slot_id)
        print(f"  {row.slot_id:<24} {question}")

# %% [markdown]
# ## 7. What this means for the experiment
#
# - The three corpora are not interchangeable: they differ in passage length,
#   coverage and the mix of attachments. Results are reported per experiment and
#   never pooled.
# - Coverage says how much of a rewrite is even in scope for measurement.
# - Spatial order (section 4) is a confounder for the temporal hypothesis, and it
#   is small enough here to state explicitly rather than control for.
# - None of this is evidence about model behaviour. It is the shape of the
#   instrument before the instrument has been used.
