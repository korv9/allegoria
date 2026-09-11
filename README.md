# Allegoria / Simulacria

> **If we validate data as it moves through a pipeline, why don't we validate meaning as it
> moves through AI?**

A research project measuring how meaning degrades under recursive LLM transformation of Swedish
statutory text. The central claim is that degradation has a **direction** — normative tightening
or loosening — and that the direction can be computed deterministically rather than judged by a
model.

The data foundation is a source-traceable Swedish-law corpus built on Databricks. That part is
done. The research machinery is what gets built next.

**Start here:**

| Document | What it covers |
| --- | --- |
| [`IDEA.md`](IDEA.md) | The research premise, the founding observation, relation to prior work |
| [`DIRECTION.md`](DIRECTION.md) | The `direction` metric — definition, derivation rule, test cases |
| [`PROTOCOL.md`](PROTOCOL.md) | Blinding, extraction wording, prompt neutrality, preregistration |
| [`CLAUDE.md`](CLAUDE.md) | Working context for Claude Code: state, decisions, sequencing |
| [`DATA_DECISIONS.md`](DATA_DECISIONS.md) | Every durable source, schema and transformation choice |

## The founding observation

A run on a passage containing a duty, an exception, and a qualifier on that exception produced an
unpredicted result: **the qualifier died before the exception did.**

What remained was an exception with no condition attached — so a permission *broadened* rather
than disappeared. Measured as information loss this looks like mild degradation. Measured as
legal effect, it is a different rule.

Existing work on iterative LLM generation measures distance from the source — BLEU, ROUGE,
BERTScore, cosine. All of it unsigned. It can say meaning moved; it cannot say which way. The
contribution here is the sign, computed against constructed ground truth, with a twinned
authentic/fictional corpus isolating memorization. See [`IDEA.md`](IDEA.md).

## Data foundation

Ordinary PySpark keeps transformations visible. `adidas/lakehouse-engine` handles Delta reads,
declared Data Quality, and Delta writes.

```text
Riksdagen SFS API
      |
      | exact XML + SHA-256
      v
50 checked-in source snapshots
      |
      | full source-shaped JSON payloads
      v
Bronze: 50 searchable law snapshots
      |
      v
Silver: 1,952 parsed provisions
      |
      +---------------------------+
      v                           v
Gold profile: 1,001 groups   Gold chunks: 1,967 chunks
```

All laws share one table in each layer:

| Layer | Managed Delta table | Checked-corpus contract |
| --- | --- | ---: |
| Bronze | `dev_lakehouse.bronze_allegoria.sfs_documents` | 50 documents |
| Silver | `dev_lakehouse.silver_allegoria.sfs_provisions` | 1,952 provisions |
| Gold profile | `dev_lakehouse.gold_allegoria.sfs_provision_summary` | 1,001 groups |
| Gold chunks | `dev_lakehouse.gold_allegoria.sfs_retrieval_chunks` | 1,967 chunks |

Bronze retains the complete raw XML payload, text, source HTML, metadata, source URL, payload
size, and a Spark-verified SHA-256 in each row. It does not persist local Workspace paths. Silver
never deduplicates legal text: repeated source anchors are preserved with an occurrence number.
Gold keeps the descriptive profile separate from source-faithful chunks.

The chunk table predates the decision to drop retrieval from scope. It is retained because it is
built and harmless, but nothing in the research path consumes it.

### Fifty-law selection

The corpus always includes six employment-related seed laws: LAS, MBL, Semesterlagen,
Arbetstidslagen, Föräldraledighetslagen, and Diskrimineringslagen. It is filled to 50 with the
newest SFS titles containing `lag (` or `balk (`; titles containing `förordning` are excluded.
The resolved document IDs and raw hashes are frozen in `data/source/sfs/manifest.json`.

Riksdagen uses the same SFS document ID as consolidated text changes. Therefore each Bronze row
has both a stable `document_id` and a version-specific `document_snapshot_id` containing its raw
SHA-256.

### Two pools

The fifty laws above are **v1**, the frozen experimental corpus. A second pool, **v2**, exists
only to pick specimens from — a wider field to choose twinned passages out of, not a larger
experiment. The corpus stays 20–40 hand-annotated pairs regardless of how big the pool gets.

| | v1 | v2 |
| --- | --- | --- |
| Documents | 50, frozen | 496 fetched, 466 parse |
| Provisions | 1,952 | 18,836 |
| Selection rule | seeds + newest law titles, filled to 50 | identical rule, filled to 500 |
| Expected counts | asserted, never relaxed | none — the pool grows when refetched |
| `Pool.strict` | `True` — a parser failure is a regression | `False` — 30 documents legitimately have no paragraphs |
| In git | source XML + Bronze JSON committed | **manifest only** |

Every script takes `--pool v1|v2`, defaulting to `v1`:

```bash
python scripts/ingest_pool_v2.py          # resumable, rate-limited, pins its own id list
python scripts/build_silver.py --pool v2
python scripts/build_tables.py --pool v2
```

**Why the v2 bytes are not committed.** The payloads are ~98 MB against a 2.47 MB `.git` — about
forty times the repository. Only `data/source/sfs/manifest_v2.json` is tracked, carrying every
document ID, title, version and SHA-256, so the pool is reproducible from git without the
repository carrying it. The payloads live under gitignored `data/local/pool_v2/`.

v2 is additive. `data/source/sfs/manifest.json` and the fifty committed documents are never
edited or pruned by the v2 path. See `DD040`.

## Running it

### Locally — the research path

Bronze data is committed to the repo, and `sfs_parser.py` is pure Python with no Spark
dependency. Silver reproduces locally in seconds:

```bash
pip install -e ".[dev]"
python scripts/build_silver.py       # 50 documents -> 1,952 provisions
```

**`1,952` is a contract, not a log line.** `build_silver.py` asserts it and exits non-zero on any
mismatch, together with the document count, uniqueness of every derived `provision_id`, and the
presence of a `source_sha256` on every row. A mismatch means the parser, the data or the
environment is wrong — not that the number moved. The same assertions run in CI via
`tests/test_candidate_markers.py`, which rebuilds from the committed Bronze rather than trusting
any generated file.

Then build the analysis tables and query them:

```bash
python scripts/find_candidates.py            # ranked shortlist, printed
python scripts/build_tables.py               # data/local/tables/*.parquet
python scripts/query.py -c "select count(*) from candidates"
```

Nothing in the research roadmap requires Spark, a cluster, or the Databricks CLI.

### The analysis layer

`build_tables.py` writes four Parquet tables, and `query.py` is a thin DuckDB wrapper that
registers them as views and runs SQL from `-c` or stdin. No ORM, no schema layer.

| Table | Grain | v1 rows |
| --- | --- | ---: |
| `provisions` | one per parsed provision | 1,952 |
| `candidates` | one per surfaced candidate, ranked | 461 |
| `marker_hits` | one per marker occurrence, **across all provisions** | 8,983 |
| `markers` | the marker inventory itself | 28 |

`marker_hits` deliberately covers every provision, not only candidates, so near-misses and
never-firing markers stay answerable. Worked queries — candidate counts by document, determinacy
distribution, marker frequency, near-misses — are in [`docs/queries.md`](docs/queries.md).

Two determinacy figures are reported and they are not interchangeable: `determinacy` grades the
whole provision and drives the ranking score, while `qualifier_determinacy` grades the qualifier
clause itself, which is what the ladder in [`DIRECTION.md`](DIRECTION.md) is actually about and
what specimens are selected on.

### In Databricks — the pipeline path

Open each file in a Databricks Git folder and choose **Run all** in order:

1. `products/allegoria/setup/setup_catalog.py`
2. `products/allegoria/bronze/bronze_sfs.py`
3. `products/allegoria/silver/silver_sfs.py`
4. `products/allegoria/gold/gold_sfs.py`
5. `products/allegoria/gold/gold_sfs_retrieval_chunks.py`

Each notebook installs its own pinned dependencies and restarts Python before imports. They do
not require `databricks.yml`; the bundle is optional automation over the same notebook paths.

The default catalog is `dev_lakehouse`, overridable with `ALLEGORIA_CATALOG`. The Databricks
identity needs permission to create/use the catalog and schemas and to create, modify, and select
the managed tables.

Table counts are verified locally against the checked-in corpus. The Delta pipeline has not yet
been run and inspected in Databricks — this is a known gap in the pipeline path, not a blocker
for the research path.

### Refreshing the source corpus

Run only when intentionally taking a new 50-law snapshot:

```powershell
python -m products.allegoria.sfs_ingestion
```

Discovery and all 50 detail responses must validate before files are changed. The entrypoint
stores exact response bytes under `data/source/sfs`, complete JSON payloads under
`data/bronze/sfs`, prunes files outside the resolved 50-document manifest, and uses only the
Python standard library.

**Do not refresh mid-experiment.** A run is bound to a corpus hash; changing the corpus
invalidates it.

## Repository structure

```text
CLAUDE.md                       working context for Claude Code
IDEA.md                         research premise
DIRECTION.md                    the direction metric
PROTOCOL.md                     measurement protocol
DATA_DECISIONS.md               decision log

products/allegoria/             Databricks medallion pipeline
|-- setup/setup_catalog.py
|-- bronze/bronze_sfs.py
|-- silver/silver_sfs.py
|-- gold/gold_sfs.py
|-- gold/gold_sfs_retrieval_chunks.py
|-- retrieval_chunks.py
|-- sfs_ingestion.py
|-- sfs_parser.py               pure Python, framework-independent
`-- README.md

simulacria/                     the research core, an installed package
|-- selection/                  heuristics: what is worth looking at
|   |-- markers.py              Swedish deontic marker sets
|   |-- determinacy.py          the determinacy ladder
|   |-- pools.py                pools, the Silver build, the count contract
|   |-- shortlist.py            scoring and ranking
|   `-- tables.py               read access to the Parquet tables
`-- measurement/                PLANNED — direction.py, contracts.py
                                must never import from selection

scripts/                        thin CLI wrappers, exporting nothing
|-- build_silver.py             bronze JSON -> provisions.jsonl
|-- find_candidates.py          duty / exception / qualifier shortlist
|-- build_tables.py             Parquet analysis tables
|-- query.py                    SQL over those tables
|-- ingest_pool_v2.py           fetch the v2 selection pool
|-- audit_markers.py            marker, determinacy and ceiling audits
|-- score_om_inte.py            score a pattern against the frozen gold set
|-- write_specimens.py          render the specimen sheet
`-- investigations/             scaffolding for closed investigations

notebooks/
`-- 01_pipeline_walkthrough.py  # %% cells; every cell calls library code
                                export to .ipynb with scripts/export_notebook.py

review/<date>/                  one dated directory per working session
|-- REVIEW.md                   decisions, predictions, how each claim was checked
|-- SPECIMENS.md                candidates for the twinned corpus
|-- DIRECTION-ceiling-proposal.md   pending specification change
`-- evidence/                   measurement outputs the above cites

corpus/                         PLANNED — twinned passages, versioned
predictions/                    PLANNED — preregistered hypotheses, see PROTOCOL.md

data/
|-- source/sfs/                 50 exact XML responses + manifest + manifest_v2.json
|-- bronze/sfs/                 50 complete source-shaped JSON records
`-- local/                      gitignored working output
    |-- provisions.jsonl        v1 Silver
    |-- provisions_v2.jsonl     v2 Silver
    |-- tables/                 v1 Parquet analysis tables
    |-- tables_v2/              v2 Parquet analysis tables
    `-- pool_v2/                v2 payloads, ~98 MB, never committed
docs/
|-- data-pipeline.md            data contracts and transformation detail
|-- las-source-inspection.md
`-- queries.md                  worked SQL against the analysis tables
tests/
|-- test_allegoria_product.py   the Databricks pipeline's contracts
|-- test_candidate_markers.py   marker regression against a frozen fixture
`-- fixtures/                   must_surface.yaml, om_inte_gold.yaml — frozen evidence
databricks.yml
pyproject.toml
```

Entries marked `PLANNED` do not exist yet. Everything else is present.

## Roadmap

| Phase | Deliverable | Status |
| --- | --- | --- |
| 1 | Local Silver + candidate selection from real SFS text | **Done** |
| 2 | Twinned corpus, then Pydantic contracts | Next |
| 3 | `direction` implemented, with the test cases from `DIRECTION.md` green | |
| 4 | The transformation loop, with full run manifests | |
| 5 | Metrics across generations; the authentic/fictional retention gap | |
| 6 | Meaning Lineage graph — a DAG over meanings with `origin_type` per node | |

**Phase 2 begins with hand-annotating a single pair, not with `contracts.py`.** One passage from
[`review/2026-09-11/SPECIMENS.md`](review/2026-09-11/SPECIMENS.md), twinned and fully annotated by hand — duty,
exception or ceiling, qualifier, what each attaches to, determinacy per slot — will say more about
what the contracts need than designing them first. Writing Pydantic models before one pair exists
means guessing at the shape.

Phase 3 is the milestone that matters: at that point the contribution is implemented and verified
without a single API call having been made.

The lineage graph sits deliberately last. A visualization built before the thing it visualizes
tends to shape the measurement toward whatever renders well.

## Scope

**In:** the direction metric, corpus twinning, the recursive loop, transformation severity as an
experimental axis (paraphrase → summarize → explain → allegorize).

**Out:** retrieval and RAG — the loop takes generation N directly, nothing is retrieved. Vector
databases — 2,000 texts is a numpy array. LLM judges — anything feeding a metric is computed, not
adjudicated. A product surface — the claim stands or falls on the measurement.

## Local checks

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

`ruff format` is scoped away from `products/allegoria/` and its test file: that tree predates
`line-length = 100`, is frozen, and a permanently red check is worse than no check. Linting still
covers it.

Data contracts and transformation details are in [`docs/data-pipeline.md`](docs/data-pipeline.md);
worked analysis queries are in [`docs/queries.md`](docs/queries.md).

## Known gaps

Current as of the last working session. Nothing here blocks Phase 2.

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