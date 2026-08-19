# LAS retrieval

This document describes the first retrieval baseline over the verified LAS Gold chunks.

## Purpose

The baseline answers one question only:

> Given a Swedish query, which source-traceable LAS chunks are retrieved?

It does not generate a legal answer. Retrieval is evaluated separately before an LLM is allowed to use the results.

## Run a search

```powershell
python -m backend.retrieval.cli "sakliga skäl uppsägning" --top-k 5
```

After installing the project, the equivalent script is:

```powershell
search-las "sakliga skäl uppsägning" --top-k 5
```

Each result includes rank, BM25 score, provision and chunk IDs, legal content, official source URL, and canonical source hash.

## Flow

```text
Gold JSONL
→ load_gold_df()
→ pandas gold_df
→ in-memory SQLite FTS5 index
→ SQL MATCH + BM25 ranking
→ retrieval result_df
```

Only `retrieval_text` is indexed. Identity and lineage columns are stored as unindexed metadata and returned with every match.

The query is case-folded, split into Unicode words and numbers, deduplicated, and converted into an FTS5 prefix query joined with `OR`. A query without searchable tokens fails. A query with no matches returns an empty DataFrame; no fallback result is invented.

The SQLite index is rebuilt in memory from the committed Gold artifact. It is not another source of truth and is not committed.

## Evaluate retrieval

```powershell
python -m backend.retrieval.evaluation
```

The curated evaluation set is stored in `data/evaluation/retrieval/las.jsonl`. Each row contains:

- a stable query ID
- the Swedish query
- query type
- one or more relevant provision IDs

The first baseline contains seven queries. At `top_k=3` it currently produces:

| Metric | Result |
| --- | ---: |
| Queries | 7 |
| Hits | 6 |
| Hit@3 | 0.8571 |
| Mean reciprocal rank | 0.7857 |

Exact legal terms perform well. The natural-language query `kan min chef sparka mig utan anledning` does not retrieve the relevant `7 §` in the top three because lexical search does not understand that `sparka` can refer to `säga upp` or `avskeda`.

This observed miss is the evidence required before adding semantic retrieval. A later Databricks implementation should evaluate full-text, vector, and hybrid AI Search against the same labeled queries instead of assuming that a more advanced retriever is better.

## Result contract

| Column | Meaning |
| --- | --- |
| `rank` | Position within this query's results |
| `score` | Positive BM25 relevance score; meaningful only within the query |
| `chunk_id` | Stable Gold chunk identity |
| `document_id` | Source document identity |
| `provision_id` | Stable Silver provision identity |
| `kind` | Paragraph or transitional provision |
| `label` | Source paragraph label |
| `heading` | Source section heading |
| `part` | Chunk order within the provision |
| `content` | Source-derived legal text segment |
| `retrieval_text` | Context-prefixed indexed text |
| `source_url` | Official Riksdagen source link |
| `source_sha256` | Canonical source snapshot hash |

## Next retrieval iteration

Do not tune BM25 against seven examples until it merely memorizes them. First add more representative questions and relevance labels. Then compare:

1. lexical BM25
2. semantic embeddings
3. hybrid retrieval

The winning strategy must improve the evaluation set without breaking source lineage.
