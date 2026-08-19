# Allegoria / Simulacria

> **If we validate data as it moves through a pipeline, why don't we validate meaning as it moves through AI?**

Allegoria is an experimental legal RAG project exploring how meaning changes as information passes through generative AI. It combines data engineering, lakehouse patterns, retrieval-augmented generation, LLM evaluation, semantic drift, and AI reliability.

The project is built backend- and data-first. A frontend will be added only after the core experiment works, then integrated into [theazero/anton-portfolio](https://github.com/theazero/anton-portfolio).

## The experiment

Allegoria and Simulacria examine two different forms of representation.

### Allegoria: deliberate transformation

```text
Legal source
    ↓
Lakehouse
    ↓
Source-grounded RAG
    ↓
Grounded answer
    ↓
Allegory, metaphor, and symbols
    ↓
Meaning Quality
```

Allegoria deliberately transforms source-grounded information into another representation. The important result is not the story itself, but the analysis of what the transformation:

- preserved
- lost
- amplified
- introduced

The original source must always remain traceable.

### Simulacria: recursive distortion

```text
SOURCE₀
    ↓
representation₁
    ↓
reconstruction₁ / SOURCE₁
    ↓
representation₂
    ↓
reconstruction₂ / SOURCE₂
    ↓
...
```

Each reconstruction becomes the source for the next generation. Every generation is also compared with `SOURCE₀` to measure cumulative drift.

The transformation should remain neutral and reusable. It must not prompt toward predetermined outcomes such as kings, oppression, or hierarchy. The purpose is to observe which representational paths emerge naturally.

## Meaning Quality

Data Quality asks whether data survived a pipeline. Meaning Quality asks:

> **Did the meaning survive the AI transformation?**

Potential signals include:

- semantic similarity and drift
- factual retention
- source grounding
- entity and relation preservation
- unsupported claims
- introduced and lost concepts
- amplification
- framing drift

Some signals can be measured relatively concretely. Interpretive dimensions such as framing must be presented clearly as model-based judgments rather than objective facts.

Meaning Quality connects the project to hallucination detection, RAG evaluation, groundedness, factual consistency, and LLM evaluation.

## Data and provenance

The first domain is a small Swedish legal dataset, likely focused on employment law.

The lakehouse schema will not be designed before the real source data has been inspected:

```text
Find source → Download sample → Inspect structure → Design transformations
```

The intended medallion flow is:

```text
SOURCE → BRONZE → SILVER → GOLD → RAG
```

- **Bronze:** raw and source-faithful
- **Silver:** cleaned and structured
- **Gold:** prepared for retrieval and AI use

Exact schemas, columns, chunking, and transformation rules will be based on the actual data. Source provenance is mandatory throughout the pipeline.

The current LAS pipeline is documented in [`docs/data-pipeline.md`](docs/data-pipeline.md). All durable choices about source handling, normalization, schemas, and chunking are recorded in [`DATA_DECISIONS.md`](DATA_DECISIONS.md).

Build the committed data artifacts with:

```powershell
python -m backend.lakehouse.pipeline
```

The implementation uses explicit pandas DataFrames at every layer:

```python
bronze_df = build_bronze_df()
silver_df = build_silver_df(bronze_df)
gold_df = build_gold_df(bronze_df, silver_df)
quality_df = build_quality_df(silver_df, gold_df)
```

Transformations use explicit SQL-like pandas operations: `merge(..., how="left")`
for lineage joins, `groupby(..., as_index=False).agg(...)` for profiles, and a
final column selection for every output contract.

The local implementation stays on pandas. If the project later moves to a data
platform, the target is Databricks with PySpark; Snowflake is not part of the
architecture.

## Retrieval baseline

Search the verified Gold chunks locally with SQLite FTS5 and BM25:

```powershell
python -m backend.retrieval.cli "sakliga skäl uppsägning" --top-k 5
```

Evaluate the retriever against the labeled LAS questions:

```powershell
python -m backend.retrieval.evaluation
```

The baseline and its known lexical limitation are documented in
[`docs/retrieval.md`](docs/retrieval.md). Retrieval returns legal content with
its provision ID, official source URL, and canonical source hash; it does not
generate an answer yet.

## Meaning Lineage

Meaning Lineage may later track how concepts emerge across generations:

```text
employer [SOURCE]
    ↓
authority
    ↓
hierarchy
    ↓
ruler
    ↓
king [GENERATED]
    ↓
kingdom [EMERGENT]
```

The first implementation should remain simple, for example:

```text
concept
generation
parent_concept
source_supported
```

A graph platform will only be considered if experimental results justify it.

## Development principles

The implementation should be small, explicit, and boring in a good way.

Prefer:

- clear names and direct data flow
- small functions with explicit inputs and outputs
- few modules and dependencies
- standard Python and direct SDK usage
- lightweight data models where contracts genuinely matter
- comments that explain why, not what

Avoid:

- premature abstractions and design patterns
- unnecessary managers, services, factories, and wrappers
- generic helper modules
- excessive validation of impossible states
- large configuration systems
- microservices
- orchestration frameworks that add more complexity than they remove

The intended style is straightforward:

```python
source = load_source(path)
chunks = chunk_text(source)
answer = generate_answer(question, chunks)
allegory = generate_allegory(answer)
quality = evaluate_meaning(source, allegory)
```

Classes are appropriate only when state and behavior meaningfully belong together. Pydantic models or dataclasses are useful for structured boundaries, but not every intermediate value needs its own model.

## Simulacria MVP

The first recursive experiment should remain transparent:

```python
original = source
current = source

for generation in range(generations):
    representation = transform(current)
    reconstruction = reconstruct(representation)

    quality = evaluate_meaning(original, reconstruction)
    save_generation(
        generation,
        representation,
        reconstruction,
        quality,
    )

    current = reconstruction
```

Each reconstruction is measured against the original source, not only against the previous generation.

## Build order

1. Find a legal source.
2. Download and inspect a representative sample.
3. Design the lakehouse from the actual data.
4. Build ingestion and Bronze → Silver → Gold transformations.
5. Add basic Data Quality checks.
6. Build a simple source-grounded RAG pipeline.
7. Add the Allegoria transformation.
8. Build a Meaning Quality MVP.
9. Test the Simulacria loop in a notebook.
10. Add Meaning Lineage if the results justify it.
11. Expose a small FastAPI API.
12. Integrate the frontend into the portfolio last.

The first meaningful milestone is:

```text
Legal source
    ↓
Lakehouse
    ↓
RAG answer
    ↓
Allegory
    ↓
Meaning Quality report
```

## Repository structure

The repository will grow with the implementation rather than being filled with placeholders. Its likely shape is:

```text
allegoria/
├── backend/
│   ├── ingestion/
│   ├── lakehouse/
│   ├── rag/
│   ├── meaning_quality/
│   ├── simulacria/
│   └── api/
├── data/
├── notebooks/
├── tests/
├── docs/
├── frontend/
│   └── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

Directories and modules should be created only when working code or data gives them a real responsibility.

## Positioning

Allegoria is not simply “AI that turns laws into stories.”

> **It is an experimental legal RAG system for examining how source-grounded meaning changes through generative transformation, with a Meaning Quality layer that tracks factual and semantic distortion.**

Simulacria extends the experiment by recursively turning generated representations into new sources and measuring how meaning drifts across generations.

> **Data lineage tracks where data came from. Meaning lineage tracks where meaning came from.**
