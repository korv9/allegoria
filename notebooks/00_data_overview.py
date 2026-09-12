# %% [markdown]
# # Data overview — what exists, at which layer, right now
#
# One page that answers "what data do I actually have?". Every number below is
# counted from disk when the cell runs. Nothing is cached, simulated or filled in.
#
# The layers, in medallion order:
#
# | Layer | What it holds | Rebuildable |
# | --- | --- | --- |
# | **bronze** | original bytes plus an envelope pinning URL, time and SHA-256 | no — refetching gives new bytes |
# | **silver** | parsed records, one provision or passage per row | yes, from bronze |
# | **gold** | Parquet tables and the DuckDB projection | yes, from silver and run evidence |
# | **runs** | raw API responses and the JSONL records of an experiment | **no — irreplaceable** |
#
# Run evidence is not derived from bronze and cannot be rebuilt: a second model
# call is new evidence, not a copy of the first. Back up `data/local/runs/`.

# %%
import json
import sys
from pathlib import Path

import yaml

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from IPython.display import display

from simulacria.domains import get, names
from simulacria.generation.plan import load_config, plan
from simulacria.measurement.corpus import load_corpus

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 70)


def megabytes(paths) -> float:
    return round(sum(p.stat().st_size for p in paths) / 1e6, 2)


print(f"Project root: {ROOT}")

# %% [markdown]
# ## 1. Bronze — original bytes, one row per domain
#
# A domain adapter owns its bronze layout and verifies it on every load: the
# bytes are re-hashed and compared with the envelope before any text is used.

# %%
rows = []
for name in names():
    domain = get(name)
    if not domain.source_dir:
        rows.append({"domain": name, "language": domain.language, "documents": "inline corpus"})
        continue
    source = (
        sorted((ROOT / domain.source_dir).glob("*")) if (ROOT / domain.source_dir).is_dir() else []
    )
    bronze = (
        sorted((ROOT / domain.bronze_dir).glob("*.json"))
        if (ROOT / domain.bronze_dir).is_dir()
        else []
    )
    rows.append(
        {
            "domain": name,
            "language": domain.language,
            "documents": len(bronze),
            "source_MB": megabytes(source),
            "bronze_MB": megabytes(bronze),
            "source_dir": domain.source_dir,
            "id_format": domain.id_format,
        }
    )
display(pd.DataFrame(rows))

# %% [markdown]
# ## 2. Silver — parsed records
#
# The SFS pool is parsed into `provisions.jsonl`; the v1 count is a contract that
# the build refuses to violate. Other domains are read per passage on demand.

# %%
silver = []
for label, relative in (
    ("v1", "data/local/provisions.jsonl"),
    ("v2", "data/local/provisions_v2.jsonl"),
):
    path = ROOT / relative
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
        documents = {json.loads(line)["document_id"] for line in lines if line}
        silver.append(
            {
                "pool": label,
                "provisions": len(lines),
                "documents": len(documents),
                "MB": megabytes([path]),
                "path": relative,
            }
        )
    else:
        silver.append(
            {
                "pool": label,
                "provisions": 0,
                "documents": 0,
                "MB": 0.0,
                "path": f"{relative} (not built)",
            }
        )
display(pd.DataFrame(silver))

# %% [markdown]
# ## 3. The annotated corpora — what the experiment actually reads
#
# These are the passages with hand-drafted slots. Draft means draft: no human has
# reviewed them, and every number computed from them carries that caveat.

# %%
corpora = []
for path in sorted((ROOT / "corpus").glob("*.yaml")):
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != 2 or "domain" not in spec:
        corpora.append({"corpus": path.name, "status": "not an annotated corpus (axis input)"})
        continue
    passages = load_corpus(path, ROOT)
    corpora.append(
        {
            "corpus": path.name,
            "domain": spec["domain"],
            "passages": len(passages),
            "slots": sum(len(p["slots"]) for p in passages),
            "chars_median": int(pd.Series([len(p["text"]) for p in passages]).median()),
            "groups": ", ".join(sorted({p["group"] for p in passages})),
            "status": passages[0]["annotation_status"],
        }
    )
display(pd.DataFrame(corpora))

# %% [markdown]
# ## 4. Configured experiments — what a run would cost before you pay for it

# %%
experiments = []
for path in sorted((ROOT / "configs").glob("*.yaml")):
    config = load_config(ROOT, path.relative_to(ROOT).as_posix())
    sources, chains = plan(ROOT, config)
    transformations = len(chains) * config["generations"]
    experiments.append(
        {
            "experiment": config["experiment"],
            "language": config.get("language"),
            "passages": len(sources),
            "chains": len(chains),
            "depth": config["generations"],
            "transformations": transformations,
            "readings": transformations + len(sources),
            "config": path.name,
        }
    )
display(pd.DataFrame(experiments))

# %% [markdown]
# ## 5. Gold — the Parquet tables and the DuckDB projection

# %%
tables = ROOT / "data/local/tables"
if tables.is_dir():
    display(
        pd.DataFrame(
            [
                {"table": p.stem, "MB": megabytes([p]), "path": p.relative_to(ROOT).as_posix()}
                for p in sorted(tables.glob("*.parquet"))
            ]
        )
    )
else:
    print("data/local/tables is missing - run python scripts/pipeline/build_tables.py")

database = ROOT / "data/local/allegoria.duckdb"
if database.is_file():
    import duckdb

    with duckdb.connect(str(database), read_only=True) as connection:
        listed = connection.execute(
            "select table_schema, table_name from information_schema.tables "
            "where table_schema in ('research', 'selection') order by 1, 2"
        ).fetchall()
        display(
            pd.DataFrame(
                [
                    {
                        "schema": schema,
                        "table": table,
                        "rows": connection.execute(
                            f'select count(*) from "{schema}"."{table}"'
                        ).fetchone()[0],
                    }
                    for schema, table in listed
                ]
            )
        )
else:
    print(f"{database.name} is missing - run python scripts/pipeline/build_database.py")

# %% [markdown]
# ## 6. Runs — the evidence that cannot be rebuilt
#
# Status is read from each manifest. `partial` means exactly that, and a run
# recorded with models this code no longer supports is listed as unreadable
# rather than quietly skipped.

# %%
from simulacria.generation.provider import supported

runs = []
for manifest_path in sorted((ROOT / "data/local/runs").glob("*/manifest.json")):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    models = (manifest.get("transformer_model", ""), manifest.get("extractor_model", ""))
    directory = manifest_path.parent
    runs.append(
        {
            "run": directory.name[:28],
            "experiment": manifest.get("experiment", "(pre-config run)"),
            "status": manifest.get("status"),
            "generations": manifest.get(
                "completed_transformations", len(list(directory.glob("generations.jsonl")))
            ),
            "readings": manifest.get("completed_readings"),
            "raw_files": len(list((directory / "raw").glob("*.json"))),
            "MB": megabytes(list(directory.rglob("*"))),
            "usd": manifest.get("usage_cost_estimate_usd"),
            "readable_now": all(supported(m) for m in models),
            "models": " / ".join(models),
        }
    )
display(pd.DataFrame(runs) if runs else "No runs yet. Nothing has been generated.")

# %% [markdown]
# ## 7. What to back up
#
# Everything below is either irreplaceable evidence or cheap to rebuild. The
# distinction is the only one that matters when clearing space.

# %%
display(
    pd.DataFrame(
        [
            {
                "path": "data/source/",
                "kind": "original bytes",
                "rebuildable": "no (refetch differs)",
                "backup": "yes",
            },
            {"path": "data/bronze/", "kind": "envelopes", "rebuildable": "no", "backup": "yes"},
            {
                "path": "data/local/runs/",
                "kind": "API receipts and run records",
                "rebuildable": "no",
                "backup": "yes, first",
            },
            {
                "path": "corpus/, prompts/, configs/",
                "kind": "experiment specification",
                "rebuildable": "no",
                "backup": "in git",
            },
            {
                "path": "data/local/provisions*.jsonl",
                "kind": "silver",
                "rebuildable": "yes",
                "backup": "no",
            },
            {
                "path": "data/local/tables*/",
                "kind": "gold Parquet",
                "rebuildable": "yes",
                "backup": "no",
            },
            {
                "path": "data/local/allegoria.duckdb",
                "kind": "gold projection",
                "rebuildable": "yes",
                "backup": "no",
            },
        ]
    )
)
