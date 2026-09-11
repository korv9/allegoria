# Agent guidance

Read [README.md](README.md) for the current workflow, repository map and build order.
Read [IDEA.md](IDEA.md) for the research premise and [PROTOCOL.md](PROTOCOL.md)
for measurement requirements. Do not duplicate the roadmap here.

## Invariants

- Keep the corpus Swedish; preserve original source bytes, URLs and SHA-256 lineage.
- Selection heuristics are not measurement. Measurement must not import selection.
- Read `DIRECTION.md` before implementing direction; resolve contradictions rather than
  inventing semantics. Case 9 and the ceiling proposal remain unresolved.
- Model slot readings are exploratory observations, not a validated judge of direction.
  Literal quote nonmatches do not establish semantic absence.
- Never fabricate generation outputs or fill notebook gaps with simulated results.
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
The user requested SQL exploration on 2026-09-11: `simulacria/analysis.py` builds a
transactional DuckDB projection. Its tables can be recreated; original run evidence
cannot. Back up ignored run directories separately. Do not add dbt at this stage.
See [docs/data-analysis.md](docs/data-analysis.md) for the implemented contract.

## Current scope

The model provider is Anthropic only, from 2026-09-11: `claude-sonnet-5` transforms,
`claude-haiku-4-5-20251001` reads (cheapest pair, DD047), key in `LLM_API_KEY`, all I/O
in `simulacria/anthropic_io.py`.
No Anthropic run exists yet. One partial OpenAI recursive run survives in
`data/local/runs/` as preserved evidence; `load_run` refuses it by name and it cannot be
resumed. Gen 1 and recursive generation are implemented; deterministic direction is not.
The normative-axis notebook contains actual source-only lexical results.

Python 3.12, ruff, 100-character lines, at most 300 executable lines per code file.
Keep durable decisions in `DATA_DECISIONS.md` and bounded task state in `CONTINUITY.md`.
