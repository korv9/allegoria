# Architecture

Two ideas hold this repository together. The **medallion layers** say where data
is allowed to live and what may be rebuilt. The **package seams** say which code
may know about what. Everything else is detail.

## The layers

| Layer | On disk | Written by | Rebuildable |
| --- | --- | --- | --- |
| bronze | `data/source/<domain>/`, `data/bronze/<domain>/` | `scripts/pipeline/ingest_*.py` | no — a refetch is new bytes, not the same bytes |
| silver | `data/local/provisions*.jsonl` | `scripts/pipeline/build_silver.py` | yes, from bronze |
| gold | `data/local/tables*/`, `data/local/allegoria.duckdb` | `scripts/pipeline/build_tables.py`, `build_database.py` | yes, from silver and run evidence |
| run evidence | `data/local/runs/<run_id>/` | `scripts/run/pilot.py`, `scripts/run/chains.py` | **no** |

Run evidence is the exception to the flow: it is not derived from bronze. A raw
API response, its hash, the request that produced it and the JSONL records built
from it are the only proof that a generation happened. A second call to the same
model is new evidence, not a copy. Back up `data/local/runs/` separately; the
gold layer can always be thrown away and rebuilt.

## The packages

```
simulacria/
  domains/      what a dataset is: sfs, rfc, inline  (+ base.py, the contract)
  pipeline/     bronze -> silver -> gold: silver.py, tables.py, store.py, gold.py
  generation/   the engine: provider, plan, design, receipts, pilot, chains
  measurement/  corpus loading, slot reading, quote audit, metrics
  reporting/    run verification, views, exports
  selection/    marker heuristics for finding interesting Swedish provisions
```

Allowed dependency directions, and the reason for each:

- **`measurement` must never import `selection`.** Selection decides what is
  worth looking at; measurement decides what a change means. A marker regex
  inside the instrument would put a guess where `DIRECTION.md` requires
  hand-annotated slot state. The split makes that leak a visible import.
- **`generation` and `measurement` must never import a concrete domain.** They
  go through `simulacria.domains.get(name)`. This is what makes a new dataset a
  config change rather than a code change.
- **`reporting` is read-only** over run directories. Nothing there writes into
  evidence.
- **`generation.receipts` owns money and evidence.** Every paid call goes through
  `call_recorded`, so there is no path that spends without a receipt, and
  `generation.design` freezes what a run means before the first call.
- **`products/allegoria/`** is the existing Databricks pipeline plus the SFS
  parser. The SFS domain adapter imports the parser; nothing else depends on it.

## Where a request goes

```
configs/<experiment>.yaml
  -> generation.plan.load_config      validates paths, generations, prompts
  -> measurement.corpus.load_corpus   resolves passages through domains.get(...)
  -> generation.plan.plan             passages x styles x variants = chains
  -> generation.chains.create         freezes design.json, writes the manifest
  -> generation.chains.execute        paid calls, receipts, budget settlement
  -> reporting.runs.load_run          replay-verifies every saved row
  -> pipeline.gold.build_database     projects verified runs into DuckDB
  -> notebooks/                       read the projection and the raw evidence
```

Each arrow is a boundary a test crosses. `tests/test_domains.py` covers the
first three, `tests/test_recursive.py` and `tests/test_run_resilience.py` the
paid path, and `tests/test_generation_one.py` the projection.

## Adding a dataset

See [new-domain.md](new-domain.md). The short version: one adapter under
`simulacria/domains/`, one corpus YAML, one config, one prompt pair. No edits to
`generation/` or `measurement/`.
