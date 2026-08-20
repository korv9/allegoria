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

Print the versioned context packet instead of the human-readable result view:

```powershell
python -m backend.retrieval.cli "sakliga skäl uppsägning" --top-k 3 --context-json
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

The expanded baseline contains 30 curated, project-authored queries. At `top_k=3` it
currently produces:

| Metric | Result |
| --- | ---: |
| Queries | 30 |
| Hits | 26 |
| Hit@3 | 0.8667 |
| Mean reciprocal rank | 0.7667 |

The query-type split makes the lexical limitation visible:

| Query type | Queries | Hit@3 | Mean reciprocal rank |
| --- | ---: | ---: | ---: |
| Legal terms | 14 | 1.0000 | 0.9643 |
| Natural language | 16 | 0.7500 | 0.5938 |

The four missed natural-language questions deliberately remain in the set:

- `kan min chef sparka mig utan anledning` → `7 §`
- `kan jag be min arbetsgivare förklara varför jag arbetar deltid` → `4 a §`
- `vilken skriftlig information ska finnas om mina anställningsvillkor` → `6 c §`
- `kan en felaktigt tidsbegränsad anställning bli tillsvidare` → `36 §`

These misses use everyday wording or paraphrases that do not align reliably
with the source vocabulary. They are evidence for comparing vector and hybrid
retrieval in Databricks, not reasons to tune BM25 against the labels.

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

## Context packet

`backend.retrieval.context.build_context_packet()` is the stable boundary
between retrieval and a future model. It accepts a query, retriever identity,
and ranked result DataFrame, then produces a JSON-serializable packet:

```text
schema_version
query
retriever
chunk_count
chunks[]
    citation_id
    rank and score
    chunk, document, and provision IDs
    label, heading, and part
    source-derived content
    official source URL
    canonical source hash
```

`format_context_text()` creates prompt-ready source sections from the packet.
It uses Gold `content`, not the context-prefixed `retrieval_text`, so added
retrieval context is never mistaken for legal source text.

The builder fails on empty results, missing lineage, duplicate chunks, or
invalid ranks. It does not invent context when retrieval finds nothing.

## Next retrieval iteration

The local retrieval implementation is now the fixed lexical baseline. Do not
add a temporary local embedding model or external embedding API. In
Databricks, run the same labeled evaluation against:

1. lexical BM25
2. vector retrieval with managed embeddings
3. hybrid full-text and vector retrieval

The winning strategy must improve the full evaluation set, especially natural
language, without breaking the context-packet or source-lineage contracts.
