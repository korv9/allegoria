# Simulacria data product

Simulacria is the research core: the recursive transformation loop, the
measurement taken over it, and the lineage DAG that presents the result. Where
Allegoria turns Riksdagen's SFS corpus into source-traceable provisions,
Simulacria takes those provisions as input and studies what happens to their
meaning under repeated LLM transformation.

Its source data is model-generation events, not another copy of SFS.

## What it measures

`direction` — whether a generation has tightened or loosened the norm it came
from, relative to its parent. The full definition, the derivation rule and the
test cases are in `DIRECTION.md` at the repository root; `PROTOCOL.md` covers
how the reading is taken without the hypothesis being smuggled into it.

The classification is deterministic. It is computed from annotated slot state
and DAG parentage, never delegated to a judge model, because an instrument built
from the same kind of system it measures is not an instrument.

## What exists

The local Silver layer and candidate selection, under `scripts/`:

| Script | Output |
| --- | --- |
| `scripts/build_silver.py` | `data/local/provisions.jsonl` — 1,952 provisions from the 50 committed Bronze documents |
| `scripts/find_candidates.py` | Provisions carrying duty / exception / qualifier structure, ranked for hand-picking |

Both are pure Python over the committed Bronze JSON. They need no Spark, no
cluster and no Databricks credentials.

## What is planned

1. **Contracts** — Pydantic models for `Passage`, `Slot`, `Generation`, `RunManifest`
2. **The twinned corpus** — 20–40 hand-annotated passage pairs, each real SFS
   text paired with a fictional twin of identical structure. The retention gap
   between the twins is the memorization control
3. **`direction`** — the deterministic classifier and its unit tests
4. **The loop** — async transformation across generations, full provenance per call
5. **Metrics** — retention and direction per generation, per transform style
6. **Lineage graph** — a DAG over meanings, `origin_type` per node

## Storage boundary

Simulacria creates no Unity Catalog table and no Databricks job. One run is one
append-only JSONL file plus a `manifest.json`, written under `data/local/` and
kept out of git. The format is deliberate: runs stay git-diffable and
human-readable, and 2,000 texts do not need a database.

Allegoria's Delta tables remain the upstream product boundary. Simulacria reads
provisions that Allegoria has already made traceable; it does not write back
into them.
