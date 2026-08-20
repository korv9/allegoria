# Allegoria data product

This product prepares the verified LAS snapshot in three inspectable Databricks layers. It does
not perform retrieval, embeddings, model inference, Allegoria transformations, or Meaning
Quality evaluation yet.

```text
data/bronze/las/sfs-1982-80.json
        |
        v
dev_lakehouse.bronze_allegoria.las_documents       1 document
        |
        v
dev_lakehouse.silver_allegoria.las_provisions      92 provisions
        |
        v
dev_lakehouse.gold_allegoria.provision_summary     19 heading/type groups
```

Run the notebooks in this order:

1. `setup_allegoria/notebook.py`
2. `bronze_allegoria/notebook.py`
3. `silver_allegoria/notebook.py`
4. `gold_allegoria/notebook.py`

Open each file as a Databricks notebook and select **Run all**. Bronze, Silver, and Gold install
their own pinned dependencies in their first cell and restart Python before imports. They do not
depend on libraries configured in `databricks.yml`; only the Delta output from the preceding
notebook is required. Setup needs no package installation.

Each transformation is written as ordinary PySpark. Lakehouse Engine reads Delta inputs, runs
declared data-quality checks, and writes managed Delta tables. Bronze reads its single checked-in
JSON file on the notebook driver and turns that record into a Spark DataFrame. Every
transformation notebook ends with a one-line row and transformation summary; optional previews
show only a few columns and rows.

Environment variables:

- `ALLEGORIA_CATALOG`: target catalog, default `dev_lakehouse`
- `ALLEGORIA_DQ_ROOT`: Lakehouse Engine quality-result directory
- `ALLEGORIA_PREVIEW`: show small notebook previews, default `true`

The Gold table is deliberately descriptive rather than RAG-specific. The next data decision is
whether retrieval should consume Silver provisions directly or introduce a separate chunk table.
