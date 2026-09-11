# %% [markdown]
# # The Parquet tables — browse, describe, query
#
# **This is selection data, not measurement.** These tables point at provisions
# carrying lexical markers. They say nothing about direction or semantic shift.
# Model-run results live elsewhere: in `data/local/runs/` and in the `research`
# tables of the DuckDB file, which stay empty until a run exists.
#
# The texts themselves are Swedish statute; only this commentary is English.
# Run top to bottom. Change `POOL` in the next cell to see the other pool.

# %%
import sys
from pathlib import Path

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from IPython.display import display

from simulacria.selection.pools import POOLS
from simulacria.selection.tables import TABLE_NAMES, connect

POOL = "v1"  # "v1" = the frozen 50-law corpus, "v2" = the larger pool
TABLES_DIR = POOLS[POOL].tables_dir
connection = connect(TABLES_DIR)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 80)


def q(sql: str) -> pd.DataFrame:
    """Run SQL against the pool's Parquet files and return a DataFrame."""
    return connection.execute(sql).df()


def show(sql: str, caption: str = "") -> pd.DataFrame:
    """Like q(), but prints the result as well."""
    frame = q(sql)
    if caption:
        print(f"{caption}  ({len(frame)} rows)")
    display(frame)
    return frame


print(f"Pool {POOL}: {TABLES_DIR}")

# %% [markdown]
# ## 1. Which files exist, and how big are they
#
# Every Parquet file is registered as a view named after the file, so
# `select * from candidates` reads `candidates.parquet`.

# %%
display(
    pd.DataFrame(
        [
            {
                "table": name,
                "file": f"{name}.parquet",
                "MB": round((TABLES_DIR / f"{name}.parquet").stat().st_size / 1e6, 2),
                "rows": q(f"select count(*) as n from {name}")["n"][0],
                "columns": len(q(f"describe {name}")),
            }
            for name in TABLE_NAMES
        ]
    )
)

# %% [markdown]
# ## 2. The columns of each table
#
# `describe` is the shortest path to what a table actually holds. There is no
# schema layer to keep in sync — this comes from the file itself.

# %%
for name in TABLE_NAMES:
    show(f"describe {name}", f"{name}")

# %% [markdown]
# ## 3. The first ten rows of each table

# %%
for name in TABLE_NAMES:
    show(f"select * from {name} limit 10", f"{name}, first 10 rows")

# %% [markdown]
# ## 4. The ten highest-ranked candidates
#
# `candidates` are ranked provisions. `score` is the sum of marker weights, and
# `determinacy` says whether the duty marker is specific or unmarked. This is a
# selection measure: a high score means many markers, not clear normativity.

# %%
show(
    """
    select c.rank, c.provision_id, c.score, c.determinacy,
           c.duty_marker, c.exception_marker, c.qualifier_marker,
           p.document_title, substr(p.text, 1, 120) as text_start
    from candidates c
    join provisions p on p.provision_id = c.provision_id
    order by c.rank
    limit 10
    """,
    "Top 10 candidates",
)

# %% [markdown]
# ## 5. Distributions — what the selection is made of

# %%
show(
    """
    select determinacy, count(*) as candidates,
           round(avg(score), 1) as mean_score,
           sum(case when has_exception then 1 else 0 end) as with_exception
    from candidates group by 1 order by candidates desc
    """,
    "Candidates per determinacy",
)
show(
    """
    select m.category, m.marker, m.weight, count(h.provision_id) as hits,
           count(distinct h.provision_id) as provisions
    from markers m
    left join marker_hits h on h.marker = m.marker and h.category = m.category
    group by 1, 2, 3 order by hits desc limit 15
    """,
    "The 15 most frequent markers",
)

# %% [markdown]
# ## 6. Look up a single provision
#
# Replace `PROVISION_ID` with any id from the tables above.

# %%
PROVISION_ID = q("select provision_id from candidates order by rank limit 1")["provision_id"][0]
display(q(f"select * from provisions where provision_id = '{PROVISION_ID}'").T)
show(
    f"""
    select category, marker, matched_span, char_offset from marker_hits
    where provision_id = '{PROVISION_ID}' order by char_offset
    """,
    f"Marker hits in {PROVISION_ID}",
)
print(q(f"select text from provisions where provision_id = '{PROVISION_ID}'")["text"][0])

# %% [markdown]
# ## 7. Full-text search in the statute text
#
# The search string is Swedish because the corpus is: `endast om` is "only if".

# %%
show(
    """
    select provision_id, document_title, substr(text, 1, 150) as extract
    from provisions where text ilike '%endast om%' limit 10
    """,
    "Provisions containing 'endast om'",
)

# %% [markdown]
# ## 8. Your own queries, and CSV export
#
# Write anything in a new cell: `show("select ... from provisions")`.
#
# To open a table in Excel, call `to_csv(...)` in a cell of your own. The file
# lands under `data/local/`, which git ignores. The semicolon delimiter makes
# Swedish Excel split the columns without an import dialog.


# %%
def to_csv(sql: str, path: Path) -> Path:
    """Write a query result straight to CSV through DuckDB, bypassing pandas."""
    target = str(path.resolve()).replace("'", "''")
    connection.execute(f"copy ({sql}) to '{target}' (header, delimiter ';')")
    return path


# to_csv("select * from candidates", ROOT / "data/local/candidates.csv")

# %% [markdown]
# ## 9. The other database: model-run results
#
# `data/local/allegoria.duckdb` holds the same selection tables under the
# `selection` schema, plus the `research` tables for model runs. Rebuild it with
# `python scripts/build_database.py`; it stays empty of runs until one exists.
# The view to go to then is `research.slot_comparisons`, which lines up a source
# slot with the parent and child readings of it.

# %%
import duckdb

DATABASE = ROOT / "data/local/allegoria.duckdb"
if DATABASE.is_file():
    with duckdb.connect(str(DATABASE), read_only=True) as run_database:
        tables = run_database.execute(
            "select table_schema, table_name from information_schema.tables "
            "where table_schema in ('research', 'selection') order by 1, 2"
        ).fetchall()
        display(
            pd.DataFrame(
                [
                    {
                        "schema": schema,
                        "table": table,
                        "rows": run_database.execute(
                            f'select count(*) from "{schema}"."{table}"'
                        ).fetchone()[0],
                    }
                    for schema, table in tables
                ]
            )
        )
else:
    print(f"{DATABASE} is missing — run python scripts/build_database.py")
