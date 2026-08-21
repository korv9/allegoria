# Allegoria SFS data product

This product prepares 50 source-traceable Swedish laws in three inspectable Databricks layers.
All laws share each table; tables are separated by data responsibility, not by law.
Retrieval chunks are prepared, but no search index, embedding, model inference, symbol mapping,
or Meaning Quality evaluation exists yet.

```text
data/source/sfs/*.xml                              50 exact API payloads
        |
data/bronze/sfs/*.json                            50 full Bronze records
        |
        v
dev_lakehouse.bronze_allegoria.sfs_documents     50 law snapshots
        |
        v
dev_lakehouse.silver_allegoria.sfs_provisions    1,952 provisions
        |
        v
        |-- dev_lakehouse.gold_allegoria.sfs_provision_summary
        |                                             1,001 profile groups
        `-- dev_lakehouse.gold_allegoria.sfs_retrieval_chunks
                                                      1,967 retrieval chunks
```

The row counts above are verified against the checked-in corpus locally. The Delta outputs still
need to be run and inspected in Databricks.

Run these Databricks notebooks individually with **Run all**, in order:

1. `setup/setup_catalog.py`
2. `bronze/bronze_sfs.py`
3. `silver/silver_sfs.py`
4. `gold/gold_sfs.py`
5. `gold/gold_sfs_retrieval_chunks.py`

Bronze, Silver, and Gold install their pinned notebook dependencies before imports. The optional
`databricks.yml` job points to the same descriptive entrypoints.

## Bronze contract

`bronze_allegoria.sfs_documents` has one row per current law snapshot. It is searchable by
`document_id` and retains the complete `raw_xml`, decoded `text`, source `html`, response hash,
payload size, API URLs, source metadata, and ingestion metadata. `document_snapshot_id` combines
the law ID and raw SHA-256. Bronze recomputes the hash from `raw_xml` with Spark and fails on a
mismatch. It retains the portable source filename but not a user-specific Workspace path.

Bronze reads every JSON file under `data/bronze/sfs`; no law-specific filename or hash is embedded
in the notebook. The current checked-in corpus must contain exactly 50 unique document IDs.

## Silver contract

`silver_allegoria.sfs_provisions` contains every parsed paragraph and transition block. It keeps
document, chapter, heading, source anchor, exact normalized text, source hash, and parent snapshot
lineage. It also hashes each normalized provision text separately. Repeated source anchors are
retained and distinguished by `source_anchor_occurrence`.

## Gold profile contract

`gold_allegoria.sfs_provision_summary` is a neutral profile grouped by document, provision kind,
chapter, and heading. It carries the source snapshot and layer processing timestamps, but no
legal text. It is useful for data inspection and chunk-design decisions; it is not a RAG source
and does not create retrieval chunks.

## Gold retrieval contract

`gold_allegoria.sfs_retrieval_chunks` prepares Silver provisions for search without adding
semantic labels. A provision stays whole when its complete retrieval text is at most 2,000
characters. Only the 11 longer provisions are split, greedily, at blank lines already preserved
by Silver. The checked corpus produces 1,967 chunks.

Each row keeps clean legal `content` separate from `retrieval_text`, which prefixes the content
with document title, chapter, heading, and provision label. Ordered chunk content must reconstruct
the complete Silver text exactly. The table retains document, provision, chunk, source-hash, and
processing lineage and enables Delta Change Data Feed for a future AI Search Delta Sync index.

Symbols, claims, metaphor mappings, and semantic meaning labels are intentionally absent. They
belong to a later, evaluated transformation after retrieval and grounded answers work.

Environment variables:

- `ALLEGORIA_CATALOG`: target catalog, default `dev_lakehouse`
- `ALLEGORIA_DQ_ROOT`: Lakehouse Engine quality-result directory
- `ALLEGORIA_PREVIEW`: show bounded notebook previews, default `true`
