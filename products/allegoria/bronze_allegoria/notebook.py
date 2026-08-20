# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
"""Load the checked-in LAS JSON snapshot into a source-faithful Bronze Delta table."""

import json
from os import getenv
from pathlib import Path

from lakehouse_engine.engine import load_data
from pyspark.sql import functions as F

CATALOG = getenv("ALLEGORIA_CATALOG", "dev_lakehouse")
DQ_ROOT = getenv("ALLEGORIA_DQ_ROOT", "/tmp/allegoria/dq")
PREVIEW = getenv("ALLEGORIA_PREVIEW", "true").lower() == "true"
PROJECT_ROOT = Path.cwd().parents[2]
SOURCE_FILE = PROJECT_ROOT / "data/bronze/las/sfs-1982-80.json"
BRONZE_TABLE = f"{CATALOG}.bronze_allegoria.las_documents"
EXPECTED_SOURCE_SHA256 = (
    "a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b"
)

if __name__ == "__main__":
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(
            f"LAS snapshot not found at {SOURCE_FILE}. Run this notebook from its "
            "Databricks Git folder."
        )

    source_record = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    df_source = spark.createDataFrame([source_record])

    df_bronze = df_source.select(
        F.col("document_id").cast("string").alias("document_id"),
        F.col("title").cast("string").alias("title"),
        F.col("version").cast("string").alias("version"),
        F.col("issued_at").cast("string").alias("issued_at"),
        F.col("published_at").cast("string").alias("published_at"),
        F.col("retrieved_at").cast("string").alias("retrieved_at"),
        F.col("source_page_url").cast("string").alias("source_page_url"),
        F.col("source_data_url").cast("string").alias("source_data_url"),
        F.col("source_sha256").cast("string").alias("source_sha256"),
        F.col("text").cast("string").alias("text"),
        F.col("html").cast("string").alias("html"),
        F.lit(SOURCE_FILE.as_uri()).alias("source_file"),
        F.current_timestamp().alias("ingested_at"),
    )

    source_hashes = {
        row.source_sha256
        for row in df_bronze.select("source_sha256").distinct().collect()
    }
    if source_hashes != {EXPECTED_SOURCE_SHA256}:
        raise ValueError(
            f"Bronze source hash mismatch: expected {EXPECTED_SOURCE_SHA256}, "
            f"got {sorted(source_hashes)}"
        )

    load_data(
        acon={
            "input_specs": [
                {
                    "spec_id": "bronze_documents",
                    "read_type": "batch",
                    "data_format": "dataframe",
                    "df_name": df_bronze,
                }
            ],
            "dq_specs": [
                {
                    "spec_id": "bronze_quality",
                    "input_id": "bronze_documents",
                    "dq_type": "validator",
                    "store_backend": "file_system",
                    "local_fs_root_dir": f"{DQ_ROOT}/bronze",
                    "unexpected_rows_pk": ["document_id"],
                    "fail_on_error": True,
                    "dq_functions": [
                        {
                            "function": "expect_column_values_to_not_be_null",
                            "args": {"column": "document_id"},
                        },
                        {
                            "function": "expect_column_values_to_be_unique",
                            "args": {"column": "document_id"},
                        },
                        {
                            "function": "expect_table_row_count_to_be_between",
                            "args": {"min_value": 1, "max_value": 1},
                        },
                    ],
                }
            ],
            "output_specs": [
                {
                    "spec_id": "bronze_output",
                    "input_id": "bronze_quality",
                    "write_type": "overwrite",
                    "data_format": "delta",
                    "db_table": BRONZE_TABLE,
                    "options": {"overwriteSchema": "true"},
                }
            ],
        }
    )

    print(
        f"BRONZE | rows {df_source.count()} -> {df_bronze.count()} | "
        "added: source_file, ingested_at | output: Delta"
    )
    if PREVIEW:
        df_bronze.select("document_id", "version", "source_sha256").show(
            3, truncate=48
        )
