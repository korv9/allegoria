# Allegoria / Simulacria

> **If we validate data as it moves through a pipeline, why don't we validate meaning as it
> moves through AI?**

This repository is a Databricks-first portfolio project about legal data, AI representation,
semantic drift, and Meaning Quality. The current milestone is intentionally limited to a clear,
source-traceable LAS data foundation. There is no retrieval or model layer yet.

## Current pipeline

The implementation follows the same pattern as
[`korv9/portfolio-platform`](https://github.com/korv9/portfolio-platform): ordinary PySpark keeps
the transformations visible, while
[`adidas/lakehouse-engine`](https://github.com/adidas/lakehouse-engine) handles reads, declared
data-quality checks, and Delta writes.

```text
LAS JSON snapshot
      |
      v
Bronze: source-shaped legal document
      |
      v
Silver: parsed and typed provisions
      |
      v
Gold: neutral provision profile
```

Unity Catalog objects in development:

| Layer | Managed Delta table | Rows after the verified run |
| --- | --- | ---: |
| Bronze | `dev_lakehouse.bronze_allegoria.las_documents` | 1 |
| Silver | `dev_lakehouse.silver_allegoria.las_provisions` | 92 |
| Gold | `dev_lakehouse.gold_allegoria.provision_summary` | 19 |

The exact Riksdagen XML response remains the canonical source and is pinned by SHA-256. The
checked-in Bronze JSON is an inspectable document representation with the decoded source text,
HTML, metadata, and provenance. Silver is Delta, and every Silver row retains the source hash and
official URL. Gold is descriptive rather than RAG-specific so retrieval design remains an
explicit next decision.

## Repository structure

```text
products/
|-- allegoria/
|   |-- setup_allegoria/notebook.py
|   |-- bronze_allegoria/notebook.py
|   |-- silver_allegoria/notebook.py
|   |-- gold_allegoria/notebook.py
|   |-- source_parser.py
|   `-- README.md
`-- simulacria/
    `-- README.md
data/
|-- source/las/                 exact XML + provenance
`-- bronze/las/                 checked-in JSON snapshot
tests/test_allegoria_product.py
databricks.yml
DATA_DECISIONS.md
```

Simulacria is a named product boundary but has no invented pipeline. Its own Bronze data will be
real model-generation events, which do not exist yet.

## Run in Databricks

Run the notebooks individually in this order:

1. `products/allegoria/setup_allegoria/notebook.py`
2. `products/allegoria/bronze_allegoria/notebook.py`
3. `products/allegoria/silver_allegoria/notebook.py`
4. `products/allegoria/gold_allegoria/notebook.py`

Or deploy and run the Databricks Asset Bundle:

```powershell
databricks bundle deploy -t dev
databricks bundle run allegoria_medallion -t dev
```

The default catalog is `dev_lakehouse`. Override it through the bundle variable or the
`ALLEGORIA_CATALOG` environment variable. Every transformation notebook ends with a short line
showing input rows, output rows, the main change, and the storage format. Small previews can be
disabled with `ALLEGORIA_PREVIEW=false`.

The Databricks identity needs permission to create/use the catalog and schemas and to create,
modify, and select the managed tables.

## Local checks

Lakehouse Engine 2.1.1 targets Python 3.12. Full Spark-backed execution belongs in Databricks;
the local tests verify the source hash, LAS parsing contract, notebook syntax, structure, bundle
task order, and file-size limits.

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

All durable source, schema, transformation, and storage choices are logged in
[`DATA_DECISIONS.md`](DATA_DECISIONS.md). The layer-by-layer columns are documented in
[`docs/data-pipeline.md`](docs/data-pipeline.md).
