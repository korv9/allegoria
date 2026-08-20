# Allegoria / Simulacria

> **If we validate data as it moves through a pipeline, why don't we validate meaning as it
> moves through AI?**

This is a Databricks-first portfolio project about legal data, AI representation, semantic drift,
and Meaning Quality. The current milestone is a clean, source-traceable Swedish-law data
foundation. Retrieval and model layers are intentionally deferred.

## Current pipeline

Ordinary PySpark keeps transformations visible. `adidas/lakehouse-engine` handles Delta reads,
declared Data Quality, and Delta writes.

```text
Riksdagen SFS API
      |
      | exact XML + SHA-256
      v
50 checked-in source snapshots
      |
      | full source-shaped JSON payloads
      v
Bronze: 50 searchable law snapshots
      |
      v
Silver: 1,952 parsed provisions
      |
      v
Gold: 1,001 neutral profile groups
```

All laws share one table in each layer:

| Layer | Managed Delta table | Checked-corpus contract |
| --- | --- | ---: |
| Bronze | `dev_lakehouse.bronze_allegoria.sfs_documents` | 50 documents |
| Silver | `dev_lakehouse.silver_allegoria.sfs_provisions` | 1,952 provisions |
| Gold | `dev_lakehouse.gold_allegoria.sfs_provision_summary` | 1,001 groups |

These counts are locally verified against the checked-in corpus. The generalized Delta pipeline
still needs to be run and inspected in Databricks.

Bronze retains the complete raw XML payload, text, source HTML, metadata, source URL, payload
size, and SHA-256 in each row. Silver never deduplicates legal text: repeated source anchors are
preserved with an occurrence number. Gold is descriptive rather than retrieval-specific.

## Fifty-law selection

The corpus always includes six employment-related seed laws: LAS, MBL, Semesterlagen,
Arbetstidslagen, Föräldraledighetslagen, and Diskrimineringslagen. It is filled to 50 with the
newest SFS titles containing `lag (` or `balk (`; titles containing `förordning` are excluded.
The resolved document IDs and raw hashes are frozen in `data/source/sfs/manifest.json`.

Riksdagen uses the same SFS document ID as consolidated text changes. Therefore each Bronze row
has both a stable `document_id` and a version-specific `document_snapshot_id` containing its raw
SHA-256.

## Repository structure

```text
products/allegoria/
|-- setup/setup_catalog.py
|-- bronze/bronze_sfs.py
|-- silver/silver_sfs.py
|-- gold/gold_sfs.py
|-- sfs_ingestion.py
|-- sfs_parser.py
`-- README.md
products/simulacria/
`-- README.md
data/
|-- source/sfs/                 50 exact XML responses + manifest
`-- bronze/sfs/                 50 complete source-shaped JSON records
docs/data-pipeline.md
tests/test_allegoria_product.py
databricks.yml
DATA_DECISIONS.md
```

Simulacria remains a named product boundary without an invented pipeline. Its future source data
is model-generation events, not another copy of SFS.

## Run in Databricks

Open each file in a Databricks Git folder and choose **Run all** in order:

1. `products/allegoria/setup/setup_catalog.py`
2. `products/allegoria/bronze/bronze_sfs.py`
3. `products/allegoria/silver/silver_sfs.py`
4. `products/allegoria/gold/gold_sfs.py`

Bronze, Silver, and Gold install their own pinned dependencies and restart Python before imports.
They do not require `databricks.yml`. The bundle remains optional automation and uses the same
descriptive notebook paths.

The default catalog is `dev_lakehouse`. Override it with `ALLEGORIA_CATALOG`. The Databricks
identity needs permission to create/use the catalog and schemas and to create, modify, and select
the managed tables.

## Refresh the source corpus

Run only when intentionally taking a new 50-law snapshot:

```powershell
python -m products.allegoria.sfs_ingestion
```

Discovery and all 50 detail responses must validate before files are changed. The entrypoint
stores exact response bytes under `data/source/sfs`, complete JSON payloads under
`data/bronze/sfs`, prunes files outside the resolved 50-document manifest, and uses only the
Python standard library.

## Local checks

```powershell
python -m pip install -e ".[dev]"
python -m ruff check products tests
python -m pytest -q
```

Data contracts and transformation details are in `docs/data-pipeline.md`. Every durable source,
schema, storage, and transformation choice is logged in `DATA_DECISIONS.md`.
