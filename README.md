# Allegoria / Simulacria

Research on how normative text changes when language models rewrite it, recursively.
The question is whether duties, exceptions and their conditions survive, and whether
changes loosen or tighten a norm. That direction metric is not implemented yet.

The corpus that started it is Swedish statute, but the dataset is a parameter: a new
one is an adapter plus a config, not an edit to the engine. English IETF RFCs ship as
the second domain.

## Start here

- [Status: what works and what is next](docs/status.md): the short, current answer.
- [Data overview notebook](notebooks/00_data_overview.ipynb): every layer counted from
  disk -- bronze bytes, silver records, gold tables, run evidence, and what to back up.
- [Architecture](docs/architecture.md): the medallion layers and the package seams.
- [Adding a dataset](docs/new-domain.md): the four files a new corpus needs.
- [Choosing models](docs/models.md): the registry, what is verified, and what the
  cheap reader costs in quality.
- [Exploratory analysis](eda/README.md): five notebooks that look at the data with
  no model involved -- corpus shape, marker failure modes, shortlist quality, slots.
- [Normative-axis notebook](notebooks/02_normative_axis.ipynb): executed lexical
  comparisons of virtue descriptions, categorical duties, conditional controls and law.
- [Parquet table browser](notebooks/05_parquet_tables.ipynb): schemas, first rows and
  distributions of the selection tables, with a CSV export helper. Selection data, not measurement.
- [Data structure and SQL](docs/data-analysis.md): storage, keys, lineage and worked queries.
- [Research premise](IDEA.md), [direction specification](DIRECTION.md),
  [measurement protocol](PROTOCOL.md), [normative axis](NORMATIVE_AXIS.md).

## Local workflow

Python 3.12. Install the local development dependencies when setting up a new environment:

```powershell
python -m pip install -e ".[dev]"
python scripts/pipeline/build_silver.py
python scripts/pipeline/build_tables.py
python scripts/pipeline/build_database.py
python scripts/report/query.py --database data/local/allegoria.duckdb -c "SELECT count(*) FROM selection.provisions"
```

The checked-in v1 corpus contains 50 law snapshots and produces exactly 1,952 provisions.
The selection tables contain 461 candidates, 8,983 marker occurrences and 28 marker definitions.
These are lexical selection aids, not measured normative slots.

For a separately authorized real model pilot, put an Anthropic key in `LLM_API_KEY` in the
ignored `.env` (see `.env.example`). Models are declared in `configs/models.yaml` and chosen
per experiment: `sonnet-5` transforms and `haiku-4-5` reads by default, the cheapest pair.
See [docs/models.md](docs/models.md) for the evidence behind that choice, what `verified`
means, and how to switch model or provider.

Which passages, prompts and depth a run uses come from a config under `configs/`.
`--check` plans and validates everything without making a single call:

```powershell
python scripts/run/pilot.py  --check                               # configs/pilot-sv.yaml
python scripts/run/chains.py --check --config configs/rfc-en.yaml  # the English domain
python scripts/run/pilot.py                                        # spends, up to --limit-usd
python scripts/pipeline/build_database.py
python scripts/report/export_notebook.py notebooks/03_generation_one.py --execute
```

The pilot takes three original provisions through four styles with two prompt variants:
24 independent generation-one texts, followed by 27 blinded model slot readings including
three originals. It is exploratory: draft annotations, one transformer, no human agreement,
no validated direction result. The local reservation limit is USD 0.50. It needs API access
and available account credit. The database build and notebooks make no API calls.

## Repository map

| Path | Responsibility |
| --- | --- |
| `simulacria/domains/` | What a dataset is: `sfs`, `rfc`, `inline`, and the adapter contract |
| `simulacria/pipeline/` | Bronze to silver to gold: parsing, Parquet tables, the DuckDB projection |
| `simulacria/generation/` | The experiment engine: provider I/O, plan, pilot, recursive chains |
| `simulacria/measurement/` | Corpus loading, blinded slot reading, quote audit, metrics |
| `simulacria/reporting/` | Run verification, notebook views, portable exports |
| `simulacria/selection/` | Marker heuristics for finding Swedish provisions worth reading |
| `scripts/pipeline/` | Ingest and build commands, in medallion order |
| `scripts/run/` | The two commands that spend money: `pilot.py`, `chains.py` |
| `scripts/report/` | Query, export a run, export a notebook, print the shortlist |
| `scripts/investigations/` | One-off studies that produced a dated artifact under `review/` |
| `configs/` | One YAML per experiment: corpora, prompts, depth, models -- plus `models.yaml`, the registry |
| `simulacria/providers/` | One module per LLM API: `anthropic` (verified), `openai` (fixtures only) |
| `corpus/` | Versioned passage specifications and draft slot annotations |
| `prompts/sv/`, `prompts/en/` | Transformer styles and the reader instruction, per language |
| `predictions/` | Dated design notes and amendments; never edited after the fact |
| `notebooks/` | Read and explain actual results |
| `eda/` | Model-free exploration of the data and of what it can support |
| `data/source/`, `data/bronze/` | Original bytes and their envelopes, per domain; preserve |
| `data/local/` | Run evidence and rebuildable analysis outputs; see backup rules below |
| `products/allegoria/` | Existing Databricks pipeline plus the shared SFS parser |
| `review/` | Dated evidence, specimen sheets and unresolved investigations |
| `docs/` | Architecture, data contracts, SQL, status |
| `tests/` | Regression and provenance checks |

`products/` is code; `data/` is data. Bronze JSON and source XML serve different
contracts: the former carries parsed metadata, the latter preserves exact response bytes.
Do not remove either as a duplicate without a tested source-contract migration.
The obsolete cache-only `backend/` tree and empty LAS/retrieval data folders were removed.

## Data architecture

Use medallion as a progression of evidence: raw sources and API receipts, verified texts
and slot observations, then analysis queries. Use DuckDB locally to query these tables.
There is no need to add dbt or a server for the current experiment.

`data/local/allegoria.duckdb` is a rebuildable analysis database. The original XML,
corpus/prompt files and `data/local/runs/<run_id>/` are the evidence it is built from.
**Back up runs separately: they are gitignored and cannot be regenerated identically.**
See [the concrete data guide](docs/data-analysis.md) for table grains and keys.

The existing Databricks implementation remains available under
[products/allegoria](products/allegoria/README.md); its retrieval chunks are historical
and unused by the active experiment. Nothing here requires running a cluster.
Detailed legacy contracts remain in [data-pipeline.md](docs/data-pipeline.md).

The optional v2 selection pool has 496 fetched documents and 18,836 parsed provisions.
Its manifest is tracked; its payloads are under `data/local/pool_v2/`.
29 documents have no paragraph structure and one has a known parser defect.
Use `--pool v2` consistently when building Silver, selection tables and the database.
A database contains one selection pool at a time; use separate database filenames to compare pools.
Do not refresh either source pool during an experiment.

## Build order and checks

1. Preserve and parse real sources; reproduce the frozen v1 counts.
2. Inspect passages and review draft source slots; run the exploratory Gen 1 pilot.
3. Resolve the direction specification and validate deterministic measurement.
4. Extend to recursive generations and twinned controls with preregistered parameters.
5. Export verified results for a portfolio demo; build the presentation after results exist.

Where the work actually stands in that order, and what unblocks what, is in
[docs/status.md](docs/status.md).

```powershell
python -m ruff check .
python -m pytest -q
```

Decisions live in [DATA_DECISIONS.md](DATA_DECISIONS.md). Agent-specific guardrails
live in [CLAUDE.md](CLAUDE.md); the workflow and repository map are maintained here.

## Known gaps

Current as of the last working session. These limitations remain unresolved.

- **The Delta pipeline has still not been run in Databricks.** Every table count is verified
  locally against the checked-in corpus; none has been observed in Unity Catalog. There is also a
  latent break: `bronze_sfs.py` persists `bronze_ingested_at` while `silver_sfs.py` selects
  `ingested_at`, so Silver would fail to resolve the column against a real Bronze table. See
  `DD041`.
- **30 v2 documents do not parse.** 29 legitimately have no paragraph structure — repealing acts,
  treaty acts whose operative text is one sentence — identified by carrying no `§` at all. The
  30th, `sfs-2023-692`, is a parser defect: it has ten well-formed paragraphs and is discarded
  because its transitional marker is written `SFS 2023:692` inline rather than alone on a line.
  v1 is measurably unaffected. See `DD042`.
- **The wildcard-gap marker audit is open.** `om inte` and `får inte` both use a `\w+` gap standing
  in for "same clause", which regex cannot express. `om inte` crosses a clause boundary in 6.2% of
  v2 hits. A fix is scored and proposed in [`review/2026-09-11/REVIEW.md`](review/2026-09-11/REVIEW.md) but not shipped:
  the prescribed allowlist costs 45.8 points of recall, and the variant that works uses a wildcard
  token class. Awaiting a decision.
- **`ceiling` is pending ratification.** `dock` marks both a carve-out from a duty and an upper
  bound on a permission, and removing one tightens where removing the other loosens. The proposed
  specification change is in
  [`review/2026-09-11/DIRECTION-ceiling-proposal.md`](review/2026-09-11/DIRECTION-ceiling-proposal.md);
  `DIRECTION.md` is unchanged until it is approved.
- **One test is deliberately red.** `test_fixture_provisions_hit_their_markers` fails on
  `sfs-2026-1283:K5P1`, whose determinacy moved `unmarked → specific` when the number-word list was
  extended. The fixture pinned that provision precisely to record the gap that was closed. Frozen
  fixtures are not edited to make a run green, so it stays failing until a human decides.
