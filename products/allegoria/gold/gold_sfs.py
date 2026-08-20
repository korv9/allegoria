# Databricks notebook source
# MAGIC %pip install "lakehouse-engine[dq]==2.1.1"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

"""Aggregate all Silver SFS provisions into a neutral data profile."""

from os import getenv

from lakehouse_engine.engine import load_data
from pyspark.sql import functions as F

CATALOG = getenv("ALLEGORIA_CATALOG", "dev_lakehouse")
DQ_ROOT = getenv("ALLEGORIA_DQ_ROOT", "/tmp/allegoria/dq")
PREVIEW = getenv("ALLEGORIA_PREVIEW", "true").lower() == "true"
SILVER_TABLE = f"{CATALOG}.silver_allegoria.sfs_provisions"
GOLD_TABLE = f"{CATALOG}.gold_allegoria.sfs_provision_summary"

READ_ACON = {
    "input_specs": [
        {
            "spec_id": "silver_table",
            "read_type": "batch",
            "data_format": "delta",
            "db_table": SILVER_TABLE,
        }
    ],
    "output_specs": [
        {
            "spec_id": "silver_provisions",
            "input_id": "silver_table",
            "data_format": "dataframe",
        }
    ],
}

if __name__ == "__main__":
    df_silver = load_data(acon=READ_ACON)["silver_provisions"]

    df_enriched = df_silver.withColumn(
        "text_char_count",
        F.length("text").cast("int"),
    )

    df_gold = (
        df_enriched.groupBy(
            "document_snapshot_id",
            "document_id",
            "document_title",
            "document_version",
            "kind",
            "chapter",
            "heading",
            "source_page_url",
            "source_sha256",
            "bronze_ingested_at",
        )
        .agg(
            F.countDistinct("provision_id").cast("long").alias("provision_count"),
            F.min("order").cast("int").alias("first_order"),
            F.max("order").cast("int").alias("last_order"),
            F.min("text_char_count").cast("int").alias("min_text_chars"),
            F.round(F.avg("text_char_count"), 1).alias("average_text_chars"),
            F.max("text_char_count").cast("int").alias("max_text_chars"),
            F.max("silver_transformed_at").alias("silver_transformed_at"),
        )
        .withColumn("gold_aggregated_at", F.current_timestamp())
        .orderBy("document_id", "first_order", "kind", "chapter", "heading")
    )

    silver_total = df_silver.select("provision_id").distinct().count()
    gold_total = df_gold.agg(F.sum("provision_count").alias("total")).first().total
    if gold_total != silver_total:
        raise ValueError(
            f"Gold aggregates {gold_total} provisions, but Silver contains {silver_total}"
        )

    load_data(
        acon={
            "input_specs": [
                {
                    "spec_id": "provision_summary",
                    "read_type": "batch",
                    "data_format": "dataframe",
                    "df_name": df_gold,
                }
            ],
            "dq_specs": [
                {
                    "spec_id": "gold_quality",
                    "input_id": "provision_summary",
                    "dq_type": "validator",
                    "store_backend": "file_system",
                    "local_fs_root_dir": f"{DQ_ROOT}/gold",
                    "unexpected_rows_pk": [
                        "document_snapshot_id",
                        "document_id",
                        "kind",
                        "chapter",
                        "heading",
                    ],
                    "fail_on_error": True,
                    "dq_functions": [
                        {
                            "function": "expect_column_values_to_not_be_null",
                            "args": {"column": "document_id"},
                        },
                        {
                            "function": "expect_column_values_to_be_between",
                            "args": {"column": "provision_count", "min_value": 1},
                        },
                    ],
                }
            ],
            "output_specs": [
                {
                    "spec_id": "gold_output",
                    "input_id": "gold_quality",
                    "write_type": "overwrite",
                    "data_format": "delta",
                    "db_table": GOLD_TABLE,
                    "options": {"overwriteSchema": "true"},
                }
            ],
        }
    )

    print(
        f"GOLD | rows {df_silver.count()} provisions -> {df_gold.count()} summary rows | "
        "changed: text length added, grouped by law and source hierarchy | output: Delta"
    )
    if PREVIEW:
        df_gold.select(
            "document_id",
            "kind",
            "chapter",
            "heading",
            "provision_count",
            "average_text_chars",
        ).show(10, truncate=48)
