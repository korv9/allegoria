# Allegoria SFS data product

This product prepares 50 source-traceable Swedish laws in three inspectable Databricks layers.
All laws share one table per layer; tables are separated by data responsibility, not by law.
There is no retrieval, embedding, model inference, or Meaning Quality evaluation yet.

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
dev_lakehouse.gold_allegoria.sfs_provision_summary
                                                    1,001 profile groups
```

The row counts above are verified against the checked-in corpus locally. The Delta outputs still
need to be run and inspected in Databricks.

Run these Databricks notebooks individually with **Run all**, in order:

1. `setup/setup_catalog.py`
2. `bronze/bronze_sfs.py`
3. `silver/silver_sfs.py`
4. `gold/gold_sfs.py`

Bronze, Silver, and Gold install their pinned notebook dependencies before imports. The optional
`databricks.yml` job points to the same descriptive entrypoints.

## Bronze contract

`bronze_allegoria.sfs_documents` has one row per current law snapshot. It is searchable by
`document_id` and retains the complete `raw_xml`, decoded `text`, source `html`, response hash,
payload size, API URLs, source metadata, and ingestion metadata. `document_snapshot_id` combines
the law ID and raw SHA-256.

Bronze reads every JSON file under `data/bronze/sfs`; no law-specific filename or hash is embedded
in the notebook. The current checked-in corpus must contain exactly 50 unique document IDs.

## Silver contract

`silver_allegoria.sfs_provisions` contains every parsed paragraph and transition block. It keeps
document, chapter, heading, source anchor, exact normalized text, source hash, and parent snapshot
lineage. Repeated source anchors are retained and distinguished by `source_anchor_occurrence`.

## Gold contract

`gold_allegoria.sfs_provision_summary` is a neutral profile grouped by document, provision kind,
chapter, and heading. It does not create retrieval chunks.

Environment variables:

- `ALLEGORIA_CATALOG`: target catalog, default `dev_lakehouse`
- `ALLEGORIA_DQ_ROOT`: Lakehouse Engine quality-result directory
- `ALLEGORIA_PREVIEW`: show bounded notebook previews, default `true`
