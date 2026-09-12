# %% [markdown]
# # Statute to generation one: what happens to the slots?
#
# Only saved model responses are read here. This notebook makes no API calls.
# A missing run raises a clear error, never sample text or simulated numbers.
#
# Run `python scripts/run/pilot.py` from the project root first.
# This is an exploratory pilot whose slot readings are not yet reviewed.

# %%
import os
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from IPython.display import HTML, display

from simulacria.reporting.runs import comparison_rows, latest_run, load_run, side_by_side

RUN = (
    Path(os.environ["ALLEGORIA_RUN_DIR"]) if "ALLEGORIA_RUN_DIR" in os.environ else latest_run(ROOT)
)
data = load_run(RUN)
print("Run:", RUN.name)
display(pd.DataFrame([data["manifest"]]).T)

# %% [markdown]
# ## Actual exposure and cost
#
# Every planned attempt is in the manifest. An aborted attempt is not an
# unchanged slot. The cost is computed from the API's token usage and the
# documented prices, without cache discounts; it is not an invoice.

# %%
print("Saved sources:", len(data["sources"]))
print("Saved generations:", len(data["generations"]))
print("Saved readings:", len(data["readings"]))
print("Run status:", data["manifest"]["status"])
print("Cost estimate USD:", data["manifest"].get("usage_cost_estimate_usd"))
display(pd.DataFrame(data["calls"])[["call_id", "event", "at"]])

# %% [markdown]
# ## Source and generation side by side
#
# Every style and prompt variant starts from the original itself, so the
# summary is not built on the paraphrase. Every produced text is shown.

# %%
sources = {s["passage_id"]: s for s in data["sources"]}
for generation in data["generations"]:
    source = sources[generation["passage_id"]]
    print(source["document_title"], generation["passage_id"])
    print(generation["style"], generation["variant"], generation["response_id"])
    print(source["source_url"])
    display(HTML(side_by_side(source, generation)))

# %% [markdown]
# ## Slot by slot
#
# `literal_status` is a reproducible search for the source quote, allowing
# whitespace variation only. A quote that is found may still be negated or
# reattached; a quote that is missing may be a correct rewording.
#
# `gen0_reader` and `gen1_reader` are another model's blinded reading, with
# verbatim quotes. They are **not human-validated ground truth**. Differences
# are review candidates. `not_read` means no reading exists, not `absent`.

# %%
comparison = pd.DataFrame(comparison_rows(data))
if comparison.empty:
    print("This run has no generated texts to compare.")
else:
    display(comparison)
    display(
        comparison.groupby(["style", "variant", "gen0_reader", "gen1_reader"])
        .size()
        .rename("slot_readings")
        .reset_index()
    )

# %% [markdown]
# ## Reading the result, and what to check next
#
# Start with the compensation condition in the daily-rest provision and the time
# limit in the dispute provision, but judge the whole table. A change read by a
# model can be a reading error. Raw responses, exact requests, source hashes,
# model versions and usage all live in the run directory.
#
# The pilot has one transformer, draft source slots and no human agreement
# measurement. It tests the workflow, not the research hypothesis. Numeric
# loosening/tightening needs verified slot attachment and a resolved direction
# contract. No such numbers are filled in here.
