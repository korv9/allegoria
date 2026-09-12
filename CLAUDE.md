# Agent guidance

Read [README.md](README.md) for the current workflow, repository map and build order.
Read [IDEA.md](IDEA.md) for the research premise and [PROTOCOL.md](PROTOCOL.md)
for measurement requirements. Do not duplicate the roadmap here.

## Invariants

- Keep each corpus in its own language -- the Swedish corpus stays Swedish, prompts and
  slot questions follow the corpus -- and preserve original bytes, URLs and SHA-256 lineage.
- Selection heuristics are not measurement. Measurement must not import selection.
- A dataset is a parameter, not a premise: `simulacria/generation` and
  `simulacria/measurement` must not import a concrete domain, and adding a corpus must
  not require editing either. See [docs/new-domain.md](docs/new-domain.md).
- Read `DIRECTION.md` before implementing direction; resolve contradictions rather than
  inventing semantics. Case 9 and the ceiling proposal remain unresolved.
- Model slot readings are exploratory observations, not a validated judge of direction.
  Literal quote nonmatches do not establish semantic absence.
- Never fabricate generation outputs or fill notebook gaps with simulated results.
- Models are declared in `configs/models.yaml` and chosen per experiment; no model id
  belongs in code. A model nobody has verified must not be used for a paid run without
  the user saying so. See [docs/models.md](docs/models.md).
- Use pinned model versions and save raw requests/responses, model IDs, sampling settings,
  prompt/code hashes and timestamps. Record dirty working-tree state honestly.
  These support traceability; they do not guarantee deterministic API replay.
- Prediction drafts are not committed preregistration. Human review must have evidence.
- Preserve frozen fixtures and dated specimen evidence; do not rewrite them to hide failures.
- Keep the existing `products/allegoria/` pipeline and entrypoints stable. Its parser is
  used by the local research code. Databricks execution is still unverified.
- No RAG or vector database is needed: each generated text has an explicit parent.
- Build and validate results before a portfolio interface or lineage graph.
- Keep dependencies minimal; do not install, commit, push or publish without authorization.

## Storage decision, superseding the previous no-database guidance

Raw run evidence remains in JSONL plus a manifest and original API response files.
The user requested SQL exploration on 2026-09-11: `simulacria/pipeline/gold.py` builds a
transactional DuckDB projection. Its tables can be recreated; original run evidence
cannot. Back up ignored run directories separately. Do not add dbt at this stage.
See [docs/data-analysis.md](docs/data-analysis.md) for the implemented contract.

## Current scope

Model choice is configuration since 2026-09-12 (DD049): `configs/models.yaml` declares
every usable model with its provider, prices and verification date, and each experiment
config names a transformer and an extractor. The default pair is `sonnet-5` and
`haiku-4-5` (cheapest, DD047). Anthropic is the only verified provider; an OpenAI
provider module exists but has never been called, and both its models are unverified.
No Anthropic run exists yet. One partial OpenAI recursive run survives in
`data/local/runs/` as preserved evidence; `load_run` refuses it by name and it cannot be
resumed. Gen 1 and recursive generation are implemented; deterministic direction is not.
The normative-axis notebook contains actual source-only lexical results.

Since 2026-09-12 the code is layered (DD048): `domains/` (sfs, rfc, inline), `pipeline/`
(bronze to silver to gold), `generation/`, `measurement/`, `reporting/`, `selection/`.
An experiment is a config under `configs/`; scripts are grouped under `scripts/pipeline`,
`scripts/run`, `scripts/report` and `scripts/investigations`. See
[docs/architecture.md](docs/architecture.md) and [docs/status.md](docs/status.md).

Python 3.12, ruff, 100-character lines, at most 300 executable lines per code file.
Keep durable decisions in `DATA_DECISIONS.md` and bounded task state in `CONTINUITY.md`.
