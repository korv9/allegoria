# Allegoria / Simulacria

Research on how normative text changes when language models rewrite it, recursively.
The question is whether duties, exceptions and their conditions survive, and whether
changes loosen or tighten a norm. The metric that answers it -- `direction` -- is
specified in [DIRECTION.md](DIRECTION.md) and now implemented as a deterministic
classifier; what is still missing is a verified model run to feed it.

The corpus that started it is Swedish statute, but the dataset is a parameter: a new
one is an adapter plus a config, not an edit to the engine. English IETF RFCs ship as
the second domain.

## The idea in plain terms

If you want the full argument, read [IDEA.md](IDEA.md). This is the short version,
enough to understand what every part of the repository is for.

**The observation.** Ask a language model to rewrite a rule, then rewrite its own
rewrite, and again -- a recursive chain. The naive expectation is that detail simply
wears away: the text gets thinner until only the main rule is left. That is not what
happens. Consider a rule with three parts:

> *Rest shall be granted. An exception may be made for an unforeseen event, provided
> compensation is given within seven days.*

After a few generations what survived was *"Rest shall be granted. An exception may be
made for an unforeseen event."* The **qualifier died before the exception did.** The
compensation condition vanished while the exception it guarded stayed. A conditional
escape hatch became an unconditional one. Measured as information loss this looks like
mild degradation; measured as legal effect, the rule got **more permissive**.

**The claim: degradation has a sign.** A rule can drift two ways. `tightening` shrinks
the set of permitted world-states (the norm binds harder); `loosening` grows it (the
norm lets more through). The whole project rests on one definition:

> **Loosening = the set of permitted world-states grows. Tightening = it shrinks.**

For any change, ask: *after it, is it easier or harder to do the thing?* Easier is
loosening, harder is tightening, neither is neutral.

**Why not cosine similarity.** The obvious metric embeds each generation and measures
distance from the source. It gives a clean falling curve -- and it is blind to this.
*"...provided compensation is given"* and *"..."* with the condition gone sit almost
on top of each other in vector space: nearly the same words, the same syntax. An
embedding calls them highly similar. The difference in legal effect is total. Every
prior study of iterative LLM drift reports unsigned measures (BLEU, chrF, ROUGE,
BERTScore, cosine). They can say meaning moved; they cannot say which way. The sign is
the contribution.

**How the sign is computed -- deterministically, not by a judge model.** A rule has up
to four moving parts: a **duty** (what shall happen), an **exception** (a carve-out), a
**ceiling** (a cap on how far a granted power reaches), and **qualifiers** (conditions
hung on any of those). During corpus construction, by hand, each slot is annotated with
which part it attaches to and its rung on a **determinacy ladder** -- `specific`
("within two years") &rarr; `vague` ("within a reasonable time") &rarr; `absent`. The
ladder matters because force drains out of a condition before the words do: "a
reasonable time" is already unenforceable while "two years" is checkable.

The sign then follows mechanically from *where* a change happens, not from what a model
thinks it means:

| A condition is weakened on a... | Sign | Why |
|---|---|---|
| duty (`ska`) | `tightening` | the duty now applies more broadly |
| exception | `loosening` | the escape hatch is easier to reach |
| ceiling | `loosening` | the cap on the power is lifted |

Removing a whole exception `tightens`; removing a whole ceiling `loosens` -- the same
surface edit, opposite signs, which is exactly why a ceiling must be its own part and
not filed under exception. `direction` is reported **per passage as a count vector**
`(tightening, loosening, neutral)` and **never netted**: a loosening and a tightening in
the same passage are two findings, not zero.

**Two controls keep it honest.**

- *Corpus twinning.* The model may have memorized real statute. So every passage has an
  **authentic** version and a **fictional twin** with identical structure -- same slot
  count, same deontic pattern -- but invented actors and numbers. The retention gap
  between the twins **is** the memorization effect, with nothing to estimate.
- *A dose-response axis.* Allegory is not a product on top of the engine; it is the most
  extreme transformation mode. `paraphrase &rarr; summarize &rarr; explain &rarr;
  allegorize` swaps out more of the text at each step. If qualifier death happens at
  generation 8 under paraphrase and generation 2 under allegory, an anecdote becomes a
  curve.

**How the pieces map to the code.** `simulacria/measurement/direction.py` is the pure
classifier (the derivation table above, plus the DD051/DD052 test cases). `changes.py`
is the honest bridge from a blinded reading -- which reports only `present` / `absent` /
`uncertain` -- to that classifier, and it *refuses to guess*: a binary reader cannot see
a `specific &rarr; vague` step, so it reports that as unobservable rather than miscount
it as neutral. The corpus carries the hand-annotated rungs. What is not built is the
part no code can supply: a verified model run to classify, human review of the draft
annotations, and a reader sharp enough to see the middle of the ladder. See
[docs/status.md](docs/status.md) for exactly where that line sits.

## Start here

- [Status: what works and what is next](docs/status.md): the short, current answer.
- [Meaning quality engine](docs/meaning-quality-engine.md): the two tracks (the
  deterministic engine vs the applications), how to make it a reusable engine, and
  how to produce drift without an LLM.
- [Simulacra: the philosophy behind the measurement](docs/simulacra.md): Baudrillard's
  four orders, deontic logic (von Wright, RFC 2119) and why the drift has a *sign*.
- [Normative drift over real version chains](scripts/investigations/normative_drift.py):
  the MUST-share of four IETF protocol families across two decades, LLM-free -- data in
  `review/2026-09-23/normative_drift.{json,csv}`.
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
- **`ceiling` is ratified; implementation and slot review remain.** `dock` marks both a carve-out from a duty and an upper
  bound on a permission, and removing one tightens where removing the other loosens. DD051/DD052
  ratify case 9/9b and the ceiling specification on 2026-09-12. The resolved proposal is in
  [`review/2026-09-11/DIRECTION-ceiling-proposal.md`](review/2026-09-11/DIRECTION-ceiling-proposal.md);
  `DIRECTION.md` contains the accepted rules and the remaining boundary ambiguity.
- **One test is deliberately red.** `test_fixture_provisions_hit_their_markers` fails on
  `sfs-2026-1283:K5P1`, whose determinacy moved `unmarked → specific` when the number-word list was
  extended. The fixture pinned that provision precisely to record the gap that was closed. Frozen
  fixtures are not edited to make a run green, so it stays failing until a human decides.
