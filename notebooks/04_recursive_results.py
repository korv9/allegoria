# %% [markdown]
# # Allegoria: actual recursive transformations
#
# **Question:** Do the conditions on an exception disappear before the exception itself?
# Can an unconditional duty acquire a new exception as it is rewritten?
#
# This notebook reads the most recent recursive run of actual model responses. It makes no
# API calls. With no run yet it stops on a clear error, never on invented data. Every source,
# intermediate text and reading can be inspected. Missing generations stay missing.
# Model readings are preliminary observations, not human-validated normative changes.

# %%
import json
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import HTML, Markdown, display

from simulacria.generation_report import latest_recursive_run, load_run
from simulacria.recursive_metrics import law_ordering, observations, planned_coverage
from simulacria.recursive_view import chain_cards, error_summary, law_curves

RUN = latest_recursive_run(ROOT)
RUN_ID = RUN.name
data = load_run(RUN)
manifest = data["manifest"]
design = json.loads((RUN / "design.json").read_text(encoding="utf-8"))
obs = observations(data)
coverage = planned_coverage(data, design)
ordering = law_ordering(data, design, obs)
pd.set_option("display.max_colwidth", 140)

# %% [markdown]
# ## 1. What is actually here to judge?
#
# `partial` means the attempt is not finished. Such a run must not be described as a
# completed experiment over ten generations. The rows below are counted from saved files.

# %%
highest = max((g["generation"] for g in data["generations"]), default=0)
display(
    pd.DataFrame(
        [
            {"Check": "Run status", "Result": manifest["status"]},
            {
                "Check": "Actual generated texts",
                "Result": f"{len(data['generations'])} / {manifest['planned_transformations']}",
            },
            {"Check": "Highest observed generation", "Result": highest},
            {
                "Check": "Complete chains to Gen 10",
                "Result": f"{coverage.complete.sum()} / {len(coverage)}",
            },
            {
                "Check": "Accepted structured readings",
                "Result": f"{len(data['readings'])} / {manifest['planned_readings']}",
            },
            {
                "Check": "Human validation",
                "Result": "Outstanding - no agreement figure exists",
            },
            {
                "Check": "Cost estimate USD",
                "Result": round(manifest.get("usage_cost_estimate_usd", 0), 4),
            },
        ]
    )
)
display(error_summary(data, RUN))
if manifest["status"] != "completed":
    display(
        Markdown(
            "**The result is incomplete.** The conclusions hold only for the texts that "
            "exist; there is no finished Gen 1-10 curve."
        )
    )
display(
    Markdown(
        f"Transformer: `{manifest['transformer_model']}`. "
        f"Reader: `{manifest['extractor_model']}`. Run: `{RUN_ID}`."
    )
)

# %% [markdown]
# ## 2. Design and traceability
#
# Three statutory passages x four styles x two prompt variants x ten generations.
# Thirty philosophical passages x paraphrase x two variants x ten generations.
# Every step uses **only the preceding text**, not the original and not model history.
# Reading happens separately and blinded, with verbatim quotes. Variants a and b are
# different instructions, not independent repetitions of the same treatment.
#
# The predictions were saved before the first call and are kept in the run's `design.json`.
# This is not a git-committed or externally timestamped preregistration. Source slots are
# drafts, the experiment has one transformer, and there are no fictional statute twins.

# %%
display(coverage)
fig, ax = plt.subplots(figsize=(10, 3.5))
actual = pd.DataFrame(data["generations"])
counts = (
    actual.groupby("generation").size().reindex(range(1, 11), fill_value=0)
    if not actual.empty
    else pd.Series(0, index=range(1, 11))
)
ax.bar(counts.index, counts.values, color="#207a87", label="Saved texts")
ax.axhline(len(design["chains"]), color="#777", linestyle="--", label="Planned per generation")
ax.set(
    xlabel="Generation",
    ylabel="Number of texts",
    title="Coverage - zero here means no texts were saved",
    xticks=range(1, 11),
)
ax.legend()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 3. Statute text: which slots are still read as present?
#
# The curves show **the share of read slots reported present**, not loosening. Missing and
# uncertain readings are reported in the table. Completed chains can differ in length, so
# do not compare generations as if the sample were constant. Wording that disappeared may
# have been reworded correctly. A phrase that survived may have changed meaning through
# negation or a different attachment.

# %%
law_counts = law_curves(obs)
display(law_counts)

# %% [markdown]
# ## 4. Testing the order in time: condition against exception
#
# Five pre-selected condition-exception pairs are followed through eight chains per
# statutory passage.
# `qualifier_first`: the condition is observed absent before the exception.
# `exception_first`: the opposite order. `same_generation`: the same observed step.
# `neither_observed_absent`: both read present throughout the planned chain.
# `unresolved`: missing generations, uncertain readings or a problem in the baseline.
#
# A first absent can be followed by present later. Such returns are shown separately and
# are not read as genuine restoration; they can equally be reading variation. A first
# absence without a complete preceding reading gets no exact point in time.

# %%
display(ordering.groupby(["style", "ordering"]).size().rename("Slot pairs").reset_index())
display(ordering)
resolved = ordering[ordering.ordering != "unresolved"]
if resolved.empty:
    display(
        Markdown(
            "**The ordering hypothesis cannot be decided on this evidence yet.** See the "
            "observed partial sequences and the source texts below."
        )
    )
else:
    display(
        Markdown(
            f"{len(resolved)} of {len(ordering)} slot pairs can be classified under the "
            "conservative ordering rule. These are observations within correlated chains, "
            "not independent trials or a significance analysis."
        )
    )

# %% [markdown]
# ## 5. Philosophical controls
#
# The philosophical texts are constructed, not quotations from Kant or Aristotle.
# Categorical duties and conditional controls are topic-matched. Virtue descriptions test a
# narrow instrument for explicit duty structure, not virtue ethics as a whole.
#
# The questions ask about explicit duty, an actually permitted exception, and a condition on
# an exception. "Without exception" does not count as a permitted exception in the reading
# question. Compare the source readings first: a conditional source may already carry
# exceptions, so its raw exception rate is not comparable to newly inserted exceptions in
# categorical texts. A change does not show that the model adopted a different ethical theory.

# %%
philosophy = obs[obs.norm_group != "statutory"]
display(
    philosophy.groupby(["norm_group", "generation", "slot_id", "status"])
    .size()
    .rename("Observations")
    .reset_index()
)
display(philosophy[philosophy.generation == 0][["passage_id", "slot_id", "status", "quote"]])
if "conditional" not in set(philosophy.loc[philosophy.status != "not_read", "norm_group"]):
    display(
        Markdown(
            "**The conditional controls have no readings.** The Kant comparison cannot be made yet."
        )
    )

# %% [markdown]
# ## 6. Read every actual chain yourself
#
# Every available chain is shown below in expandable cards, with the source and all saved
# generations. The table gives the model's status and quote. This is the material for your
# own judgement; no curve replaces reading the actual texts.

# %%
display(HTML(chain_cards(data, obs)))

# %% [markdown]
# ## 7. SQL and export
#
# The database is a rebuildable projection. `texts` carries parent links, generation number,
# style, variant and norm group. `slot_comparisons` ties source, parent and child together.
# The raw files and manifests are the evidence that must be backed up. A portable export
# contains Parquet tables, actual results as JSON and a blinded review packet. No API key is
# needed to read this notebook's saved output.

# %%
with duckdb.connect(str(ROOT / "data/local/allegoria.duckdb"), read_only=True) as connection:
    sql = """
    SELECT passage_id, generation, style, variant, slot_id,
           source_status, parent_status, child_status, child_quote
    FROM research.slot_comparisons
    WHERE run_id = ? AND parent_status IS DISTINCT FROM child_status
    ORDER BY passage_id, style, variant, generation, slot_id
    """
    display(connection.execute(sql, [RUN_ID]).df())
print("Export:", ROOT / "data/local/exports" / RUN_ID)

# %% [markdown]
# ## 8. What is still needed for a strong finding?
#
# - Complete chains to generation 10, on the same planned material.
# - Blind human review of the slot readings, reporting disagreement and uncertainty.
# - Normative direction kept separate from precision and verbatim text loss.
# - More transformer models, repeated chains and twin controls for broader conclusions.
#
# Neither a low defect rate in the test suite nor deterministic code makes a semantic
# interpretation objective. The strongest evidence is a concrete case where the original and
# the rewrite impose different requirements or permissions, checked against text and context.
