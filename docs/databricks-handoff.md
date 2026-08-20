# Databricks handoff

This document defines where local development ends and what the first
Databricks implementation must preserve. It does not prescribe workspace,
network, or production deployment settings before a real Databricks environment
is selected.

## Local completion boundary

The local foundation owns and verifies:

```text
canonical LAS source
→ deterministic Bronze, Silver, and Gold data
→ fail-fast Data Quality
→ lexical BM25 baseline
→ labeled retrieval evaluation
→ versioned context packet
```

The local phase does not own embeddings, vector infrastructure, model
inference, generated answers, or online serving.

## Migration inputs

| Local artifact | Current grain | Databricks target |
| --- | --- | --- |
| `data/source/las/sfs-1982-80.xml` | one canonical source snapshot | Unity Catalog managed volume |
| Bronze JSON | one row per document snapshot | Bronze Delta table |
| Silver JSONL | one row per legal provision | Silver Delta table |
| Gold JSONL | one row per retrieval chunk | Gold Delta table |
| Quality JSONL | one row per document and provision kind | quality Delta table |
| Retrieval evaluation JSONL | one row per labeled query | evaluation Delta table |

The PySpark implementation should translate the existing column-explicit pandas
operations directly. It must not introduce a pandas/PySpark compatibility layer.

## Contracts that must not drift

### Source lineage

Every Databricks retrieval result must retain:

- `chunk_id`
- `document_id`
- `provision_id`
- `source_url`
- `source_sha256`

The source hash must still identify the committed canonical LAS snapshot.

### Legal content

Gold `content` is the source-derived text sent to the model. `retrieval_text`
may be indexed because it adds title, heading, and label, but it must not replace
`content` in citations or Meaning Quality comparisons.

### Context packet

Databricks retrieval must produce context schema version `1.0`, matching
`backend.retrieval.context.build_context_packet()`. Search-specific scores may
have different scales, but rank, retriever identity, content, and lineage fields
remain required.

### Retrieval evaluation

The same 30 queries and relevance labels must evaluate every candidate. Report:

- Hit@3
- mean reciprocal rank
- results split by `legal_terms` and `natural_language`

The local lexical reference is:

| Slice | Hit@3 | Mean reciprocal rank |
| --- | ---: | ---: |
| All 30 queries | 0.8667 | 0.7667 |
| 14 legal-term queries | 1.0000 | 0.9643 |
| 16 natural-language queries | 0.7500 | 0.5938 |

## First Databricks sequence

1. Upload the canonical source snapshot to a governed Unity Catalog volume.
2. Reproduce Bronze, Silver, Gold, and quality outputs as Delta tables.
3. Verify row counts, stable IDs, source hash, chunk limits, and Silver
   reconstruction against the local artifacts.
4. Create Databricks AI Search indexes over the Gold table.
5. Evaluate full-text, vector, and hybrid retrieval with the committed labels.
6. Select retrieval behavior from measured results, not platform defaults.
7. Convert ranked results to context schema `1.0`.
8. Only then connect a Foundation Model API or Model Serving endpoint.
9. Require generated answers to cite retrieved source IDs and URLs.
10. Add Allegoria and Meaning Quality after grounded answer behavior is tested.

## Databricks readiness checks

The data migration is accepted only when:

- Bronze has one LAS document and the canonical source hash matches locally.
- Silver has 92 provisions and stable `provision_id` values.
- Gold has 96 chunks and reconstructs every Silver provision exactly.
- No Gold retrieval text exceeds 2,000 characters.
- All 30 evaluation labels resolve to Gold provision IDs.
- AI Search results can be converted to context schema `1.0` without losing
  legal content or lineage.

The first model call is therefore downstream of a verified data and retrieval
migration, not part of migration validation itself.
