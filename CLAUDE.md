# CLAUDE.md

Guidance for Claude Code working in `korv9/allegoria`. Read `IDEA.md` first for
the research premise; this file covers state, decisions and sequencing.

**Before implementing anything in `simulacria/direction.py`, read
`DIRECTION.md`.** It carries the definition, the derivation rule, worked
examples from real SFS text in this repo, and the test cases. `direction` is the
project's contribution — getting it wrong is not a bug, it is a different
project.

---

## What this is

A research system measuring how meaning degrades under recursive LLM
transformation of Swedish statutory text. The central claim is that degradation
has a **direction** (normative tightening vs loosening), not just a magnitude,
and that the direction can be computed deterministically.

Not a product. Not RAG. Not model collapse research. See `IDEA.md`.

---

## Repo state

**Exists and works:**
- `data/source/sfs/` — 50 raw SFS XML documents + `manifest.json`
- `data/bronze/sfs/` — 50 parsed JSON docs, each with `html`, `text`, `raw_xml`,
  provenance fields (`source_sha256`, `source_page_url`, `retrieved_at`)
- `products/allegoria/sfs_parser.py` — pure Python + BeautifulSoup, no Spark
  dependency
- `products/allegoria/{bronze,silver,gold}/` — Databricks notebooks wrapping the
  above with PySpark + lakehouse-engine
- `databricks.yml` — Asset Bundle job definition
- `DATA_DECISIONS.md` — ~39 tracked decisions, Active/Superseded

**Verified locally (2026-09-10):** looping `parse_sfs_html` over the committed
bronze JSON yields **1,952 provisions from 50 documents** — identical to the
Spark pipeline's output, with zero infrastructure.

**Does not exist yet:**
- The twinned corpus (`simulacria_corpus_v1.yaml` exists locally, uncommitted)
- Pydantic contracts
- The transformation loop
- `direction` computation
- Any metrics or lineage graph code

---

## Decisions already made — do not re-litigate

These were argued through and settled. Raise them again only if you find
evidence that contradicts the reasoning, not on general preference.

| Decision | Rationale |
|---|---|
| **No dbt migration** | Bronze/Silver are HTML parsing, not SQL. dbt python models on Databricks are just notebooks with extra layers. Reconsider only for the metrics layer if it exceeds ~10 models |
| **Run locally, not Databricks** | The research core has no Spark dependency. Bronze data is committed; Silver parses locally in seconds |
| **Keep the Databricks code** | It works, costs nothing to leave, has portfolio value. It is simply not in the critical path. Do not delete it, do not "improve" it |
| **Skip Gold for now** | `direction` needs 20–40 hand-picked passage pairs, not 1,952 aggregated rows |
| **No RAG, no vector DB** | Generation N+1 takes generation N directly. The parent is known. Nothing is retrieved |
| **Embeddings are secondary** | Cosine cannot distinguish "may, provided X" from "may". Use for plotting drift and surfacing anomalies only, never as ground truth |
| **No judge model** | `direction` and `origin_type` are computed from slot state and DAG parentage. An LLM-based instrument cannot separate the measurement from what is measured |
| **Storage is JSONL + manifest** | One run = one append-only JSONL file plus `manifest.json`. No database. Git-diffable, human-readable |
| **Allegoria is a transform mode, not a parent product** | `transform_style` enum value alongside paraphrase/summarize/explain. One repo, one engine, one loop |
| **The lineage graph ranks below the measurement** | A visualization built first tends to shape the metric toward whatever renders well |

---

## Setup

```bash
pip install beautifulsoup4 pydantic httpx sentence-transformers numpy
```

No Spark, no Databricks CLI, no cluster required for anything in the roadmap
below. `lakehouse-engine` is only needed if running the Databricks notebooks.

Embedding model when needed: `KBLab/sentence-bert-swedish-cased` (768-dim,
Swedish/English bilingual, max seq length 384, runs fine on CPU).

---

## Roadmap

### Phase 1 — Local Silver + candidate selection
- `scripts/build_silver.py` — loop bronze JSON → `parse_sfs_html` →
  `data/local/provisions.jsonl`
- `scripts/find_candidates.py` — surface provisions with rule / exception /
  qualifier structure for Anton to pick from by hand. Heuristic matching on
  Swedish deontic markers (`ska`, `får`, `får inte`, `om inte`, `under
  förutsättning att`, `dock`) is fine here — this is a shortlist for human
  selection, not a measurement
- **Output:** a reviewable candidate list

### Phase 2 — Contracts and corpus
- `simulacria/contracts.py` — Pydantic models: `Passage`, `Slot`, `Generation`,
  `RunManifest`, `TransformStyle`
- Commit `simulacria_corpus_v1.yaml` with the twinned pairs
- Validate the corpus against the contracts in CI
- **Output:** a corpus that loads and validates

### Phase 3 — `direction`
- Slot schema: what a slot is, its kind (actor / deadline / condition /
  modality), and which position it occupies (main rule vs exception)
- `simulacria/direction.py` — deterministic classification into
  `tightening` / `loosening` / `neutral`
- Unit tests using the rest-period example: dropping the compensation qualifier
  on an exception must classify as `loosening`
- **Output:** the contribution, testable in isolation

### Phase 4 — The loop
- `simulacria/loop.py` — async LLM calls, `asyncio.Semaphore(5)`, pinned model
  string, temperature recorded per call, raw response retained
- Writes JSONL per generation with full provenance
- **Output:** runnable end-to-end on the corpus

### Phase 5 — Metrics
- Retention, direction, generation-at-which-qualifier-dies, per
  `transform_style` and per authentic/fictional twin
- The twin retention gap is the memorization measure
- **Output:** the dose-response curve

### Phase 6 — Lineage graph
- `networkx` DAG, `origin_type` per node, JSON export for the UI

---

## Run manifest — required fields

Every run must record enough to reproduce it exactly:

- `run_id`, `started_at`, `finished_at`
- `model` — exact version string, never an alias
- `temperature`, `max_tokens`, any sampling parameters
- `prompt_version` — versioned, not inlined
- `transform_style` — first-class dimension, not an afterthought
- `corpus_version` and corpus file hash
- `generations` — max depth
- `code_version` — git SHA

If a field is missing, the run is not reproducible and the results are not
usable.

---

## Guardrails

- **The corpus stays Swedish.** Deontic modality in Swedish statutory text
  (`ska`, `får`, `får inte`) is what makes slot structure constructible. Do not
  translate passages or add English-language experiments
- **Never pin a model alias.** `claude-sonnet-4-5` style aliases move. Record
  the resolved version string
- **Do not add a vector database.** 2,000 texts is a numpy array
- **Do not introduce an LLM judge** for anything that feeds a metric
- **Do not build the graph UI before Phase 5** produces something to graph
- **Do not run or modify the Databricks pipeline** unless explicitly asked

---

## Open questions

The four that previously blocked Phase 3 — ternary vs scale, netting, slot
weights, altered vs removed — now have proposed answers in `DIRECTION.md`. They
are argued through but **not yet ratified in `DATA_DECISIONS.md`**. Implement
against them; escalate to Anton rather than improvising if an edge case forces a
change.

Still genuinely open:

1. How many passage pairs does the first experiment need? (Working estimate:
   20–40)
2. Which transform styles ship in the first run — all four, or paraphrase and
   allegorize as the extremes?
3. How many generations deep before the run stops?

---

## Conventions

- Python 3.12, `ruff`, line length 100
- Research code lives in `simulacria/`; the existing `products/allegoria/` tree
  is the Databricks pipeline and stays as-is
- Decisions get recorded in `DATA_DECISIONS.md` with Active/Superseded status —
  add to it rather than editing history
- Local artifacts under `data/local/` and gitignored; committed data stays in
  `data/source/` and `data/bronze/`
