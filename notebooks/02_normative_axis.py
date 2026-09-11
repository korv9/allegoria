# %% [markdown]
# # The shape of a norm — a first instrument test
#
# **The preliminary finding: the selection markers do not tell an exception from
# a denial of an exception.** They also fire on descriptive language.
# What follows are actual marker runs on constructed Swedish passages and on
# existing statutory specimens. No model generations or direction measures are
# simulated. Run top to bottom. The saved notebook contains executed results.

# %%
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from IPython.display import HTML, display

from simulacria.selection.axis import (
    digest,
    expectation_checks,
    hit_summary,
    length_summary,
    load_corpus,
    match_statutes,
    paired_lengths,
    passage_counts,
    verify_statutory_snapshot,
    virtue_failures,
)
from simulacria.selection.axis_view import cards
from simulacria.selection.highlight import legend_html, marker_html, marker_spans

philosophy = load_corpus(ROOT / "corpus/philosophy_v1.yaml")
baseline = load_corpus(ROOT / "corpus/statutory_axis_v1.yaml")
display(pd.DataFrame(verify_statutory_snapshot(baseline, ROOT)))
statutes = match_statutes(philosophy, baseline)
passages = philosophy + statutes
display(
    pd.DataFrame(
        [
            {"file": name, "SHA-256": digest(ROOT / name)}
            for name in (
                "corpus/philosophy_v1.yaml",
                "corpus/statutory_axis_v1.yaml",
                "simulacria/selection/markers.py",
            )
        ]
    )
)

# %% [markdown]
# ## 1. The axis
#
# | Type | Where the norm sits | Intended structure | Future test |
# | --- | --- | --- | --- |
# | Virtue description | Character | No explicit duty slots | Silent instrument |
# | Statute | The rule | Duty, exception, qualifier | Loss can widen permission |
# | Unconditional command | The rule | Duty without exception | An inserted exception can weaken it |
# | Conditional control | The rule | Same topic, existing exception | Control for general hedging |
#
# The virtue group is a negative control for explicit deontic structure. That does
# not mean virtue ethics carries no action norms. The control pairs make it possible
# to compare new exceptions in conditional and unconditional duties later.
# The passages are written in philosophical form, not quoted from Kant or Aristotle.
# See [method and sources](../NORMATIVE_AXIS.md). Construction reduces verbatim
# recall; it does not prove that only one variable changed.

# %% [markdown]
# ## 2. The passage forms side by side
#
# The duty pair shares an opening and differs at the end. Colour marks a regex hit,
# not an interpretation.

# %%
display(HTML(legend_html()))
display(
    HTML(
        cards(
            [
                philosophy[0],
                next(r for r in philosophy if r["passage_id"] == "categorical-01"),
                next(r for r in philosophy if r["passage_id"] == "conditional-01"),
            ]
        )
    )
)

# %% [markdown]
# ## 3. Marker hits across the axis
#
# Every passage is shown, failed control cases included. The statutes are matched on
# length alone against the unconditional commands, without replacement. The baseline
# is the already reviewed specimen list; it is not a random sample of Swedish law.

# %%
display(HTML(cards(passages)))
display(
    pd.DataFrame(
        [
            {
                k: r[k]
                for k in (
                    "passage_id",
                    "matched_to",
                    "length_difference",
                    "source_url",
                    "review_note",
                )
            }
            for r in statutes
        ]
    )
)

# %% [markdown]
# ## 4. The distribution — the measurable result so far
#
# The table counts **marker occurrences**, overlapping regexes included.
# The `passages_with_…` columns count passages with at least one hit instead.
# These are not slot counts, precision, loosening, or a test of model behaviour.

# %%
display(pd.DataFrame(hit_summary(passages)).set_index("group"))
display(pd.DataFrame(expectation_checks(passages)))

# %% [markdown]
# Lengths are in Unicode characters, whitespace and line breaks included. First the
# whole specimen baseline, then the matched selection. Quartiles use the inclusive
# method. Length matching limits one confounder; syntax and topic are not fully
# controlled.

# %%
display(pd.DataFrame(length_summary(philosophy + baseline)).set_index("group"))
display(pd.DataFrame(length_summary(statutes)).set_index("group"))
display(pd.DataFrame(paired_lengths(philosophy)))
display(pd.DataFrame(passage_counts(passages)))

# %% [markdown]
# ## 5. What we cannot show yet
#
# The following are named, **non-executable analysis cells**, with no simulated output.
# The predictions are in the [preregistration draft](../predictions/2026-09-11-normative-axis.md).
# That draft still lacks a git timestamp and complete run parameters.
#
# | Future cell | What it tests | What is missing |
# | --- | --- | --- |
# | The virtue line | P1: no new explicit norms appear | Generations, review of emergent slots |
# | Inserted exceptions | P2: categorical duties become conditional | Insertion contract, direction, generations |
# | Paired insertion rate | P3: a higher rate than in the controls | Equal exposure, uncertainty analysis |
# | The generation curve | Loosening events per transition | Verified slot transitions and manifests |
# | The passage sequence | Actual specific → vague → absent | Saved text, quote and attachment per slot |
# | Time to absent | First loss, with censoring | Complete and interrupted chains |
# | Direction asymmetry | Loosening and tightening separately | Direction and verified reading |
# | The twin gap | Authentic against fictional | Hand-annotated statute twins |
# | Human agreement | Reliability of the reading | Blind human review per slot type |
#
# A future demo can show a curve, a traceable passage sequence and these summaries.
# There is no evidence here yet for their expected direction. "Unconditional →
# conditional" is a testable change in text; "the model changed ethical theory" is
# too strong. Loosening concerns the room for permitted actions, not moral quality.

# %% [markdown]
# ## 6. Failure modes and what the finding means
#
# Negative controls are allowed to fail. No hits are filtered out to manufacture a
# desired zero row. The table below shows every virtue passage that produced hits.

# %%
failures = virtue_failures(philosophy)
print(f"Virtue passages with marker hits: {len(failures)}")
if failures:
    for row in failures:
        display(HTML(marker_html(row["text"])))
        display(pd.DataFrame(row["hits"]))
else:
    print("No virtue passage produced marker hits in this run.")

# %% [markdown]
# In the ambition description, "om ett gott liv" ("about a good life") is a
# descriptive complement, not a condition. In the promise pair, "försäkran om god
# vilja" ("an assurance of good will") is not a condition either. Bare `om` ("if",
# "about") therefore cannot identify a qualifier on its own.
#
# `undantag` ("exception") in "utan undantag" ("without exception") denies an
# exception yet produces an exception hit. The conditional closing sentence is hit by
# both `dock` ("however") and `gäller inte` ("does not apply"). Double hits are not
# two semantic exceptions. The markers are left unchanged.

# %%
for pid in ("categorical-01", "conditional-01"):
    row = next(r for r in philosophy if r["passage_id"] == pid)
    display(HTML(marker_html(row["text"])))
    display(pd.DataFrame(marker_spans(row["text"])))

# %% [markdown]
# The constructed commands contain no intended escape clause, but role and object
# bound each duty. Consent, respect and confidentiality are modern constructions in
# need of philosophical review; not all of them are established Kantian examples.
# The statute selection keeps the original review's reservations about the ceiling
# and about false exceptions. The corpus groups are development material, not
# independent validation data.
#
# **What works now is the reproducible instrument test. What fails is the assumption
# that lexical selection markers correspond directly to normative structure.**
