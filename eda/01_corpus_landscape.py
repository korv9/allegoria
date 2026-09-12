# %% [markdown]
# # EDA 1 — the corpus landscape
#
# What is actually in the parsed corpus, before any heuristic or model touches it.
# Counted from `data/local/tables/provisions.parquet`. No API calls.
#
# The point of this page is calibration: when a later result says "provisions
# with a duty and an exception behave like X", it helps to know how long a
# provision is, how unevenly they are spread across documents, and how much of
# the corpus is structural boilerplate.

# %%
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

from simulacria.pipeline.silver import POOLS
from simulacria.pipeline.store import connect

POOL = "v1"  # "v1" = the frozen 50-law corpus, "v2" = the larger pool
connection = connect(POOLS[POOL].tables_dir)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 70)


def q(sql: str) -> pd.DataFrame:
    return connection.execute(sql).df()


provisions = q("select * from provisions")
print(
    f"Pool {POOL}: {len(provisions):,} provisions from {provisions.document_id.nunique()} documents"
)

# %% [markdown]
# ## 1. How long is a provision?
#
# Length matters twice over. It drives cost directly, and it is the most obvious
# confounder in any lexical score: longer text has more room for markers.

# %%
display(provisions.char_count.describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.99]).to_frame().T)

fig, axes = plt.subplots(1, 2, figsize=(12, 3.5))
axes[0].hist(provisions.char_count, bins=60, color="#207a87")
axes[0].set(xlabel="characters", ylabel="provisions", title="Length distribution (all)")
axes[1].hist(provisions.char_count.clip(upper=2000), bins=60, color="#207a87")
axes[1].set(
    xlabel="characters (clipped at 2000)", ylabel="provisions", title="Length, long tail clipped"
)
plt.tight_layout()
plt.show()

short = (provisions.char_count < 120).mean()
print(
    f"{short:.1%} of provisions are under 120 characters — mostly headings, references and stubs."
)

# %% [markdown]
# ## 2. How evenly are provisions spread across documents?
#
# A handful of large acts can dominate any corpus-wide statistic. This is what a
# per-document weighting would have to correct for.

# %%
per_document = (
    provisions.groupby(["document_id", "document_title"])
    .agg(provisions=("provision_id", "count"), chars=("char_count", "sum"))
    .sort_values("provisions", ascending=False)
)
display(per_document.head(10))
display(per_document.provisions.describe().to_frame().T)

share = per_document.provisions.head(5).sum() / len(provisions)
print(f"The five largest documents hold {share:.1%} of all provisions.")

# %% [markdown]
# ## 3. Structure: chapters, headings and kinds
#
# `kind` comes from the parser. Anything that is not an ordinary provision is a
# candidate for exclusion in a later analysis, and it is better to see the size
# of that group now than to discover it inside a result.

# %%
display(provisions.kind.value_counts().rename("provisions").to_frame())
display(
    pd.DataFrame(
        {
            "with chapter": [provisions.chapter.notna().sum()],
            "without chapter": [provisions.chapter.isna().sum()],
            "with heading": [provisions.heading.astype(str).str.strip().ne("").sum()],
            "distinct headings": [provisions.heading.nunique()],
        }
    )
)
display(
    provisions.heading.astype(str)
    .str.strip()
    .replace("", "(none)")
    .value_counts()
    .head(12)
    .rename("provisions")
    .to_frame()
)

# %% [markdown]
# ## 4. Lineage — every provision can be traced back to bytes
#
# This is a provenance check, not a statistic: a missing `source_sha256` would
# mean a row whose origin cannot be proven, and there must be none.

# %%
missing_hash = provisions.source_sha256.astype(str).str.strip().eq("").sum()
missing_url = provisions.source_url.astype(str).str.strip().eq("").sum()
print(f"provisions without a source hash: {missing_hash}")
print(f"provisions without a source URL:  {missing_url}")
print(f"distinct source documents hashed: {provisions.source_sha256.nunique()}")
assert missing_hash == 0, "a provision without lineage must not exist"

# %% [markdown]
# ## 5. The sample the experiment actually uses
#
# Three provisions, chosen in `corpus/law_probe_v1.yaml`. Seeing them against the
# corpus distribution is the honest way to read any result from them: they are
# mid-length, ordinary provisions, and they are three.

# %%
from simulacria.measurement.corpus import load_corpus

probe = load_corpus(ROOT / "corpus/law_probe_v1.yaml", ROOT)
probe_ids = [p["passage_id"] for p in probe]
chosen = provisions[provisions.provision_id.isin(probe_ids)]
display(chosen[["provision_id", "document_title", "char_count"]])
for _, row in chosen.iterrows():
    percentile = (provisions.char_count < row.char_count).mean()
    print(f"{row.provision_id}: {row.char_count} chars, longer than {percentile:.0%} of the corpus")
