# Databricks notebook source
# MAGIC %pip install "lakehouse-engine[dq]==2.1.1"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

"""Load all checked-in SFS payloads into one searchable Bronze Delta table."""

import json
from os import getenv
from pathlib import Path

from lakehouse_engine.engine import load_data
from pyspark.sql import functions as F

CATALOG = getenv("ALLEGORIA_CATALOG", "dev_lakehouse")
DQ_ROOT = getenv("ALLEGORIA_DQ_ROOT", "/tmp/allegoria/dq")
PREVIEW = getenv("ALLEGORIA_PREVIEW", "true").lower() == "true"
PROJECT_ROOT = Path.cwd().parents[2]
SOURCE_DIR = PROJECT_ROOT / "data/bronze/sfs"
EXPECTED_DOCUMENT_COUNT = 50
BRONZE_TABLE = f"{CATALOG}.bronze_allegoria.sfs_documents"


def read_bronze_records(source_dir: Path) -> list[dict[str, object]]:
    source_files = sorted(source_dir.glob("*.json"))
    if len(source_files) != EXPECTED_DOCUMENT_COUNT:
        raise ValueError(
            f"Bronze expects {EXPECTED_DOCUMENT_COUNT} SFS JSON files in {source_dir}, "
            f"got {len(source_files)}"
        )

    records: list[dict[str, object]] = []
    for source_file in source_files:
        record = json.loads(source_file.read_text(encoding="utf-8"))
        if record.get("document_id") != source_file.stem:
            raise ValueError(
                f"Bronze file {source_file.name} contains document_id "
                f"{record.get('document_id')!r}"
            )
        record["source_file"] = source_file.as_uri()
        records.append(record)
    return records


if __name__ == "__main__":
    source_records = read_bronze_records(SOURCE_DIR)
    df_source = spark.createDataFrame(source_records)

    df_bronze = df_source.select(
        F.col("document_snapshot_id").cast("string").alias("document_snapshot_id"),
        F.col("document_id").cast("string").alias("document_id"),
        F.col("designation").cast("string").alias("designation"),
        F.col("title").cast("string").alias("title"),
        F.col("version").cast("string").alias("version"),
        F.col("department").cast("string").alias("department"),
        F.col("source_type").cast("string").alias("source_type"),
        F.col("source_subtype").cast("string").alias("source_subtype"),
        F.col("issued_at").cast("string").alias("issued_at"),
        F.col("published_at").cast("string").alias("published_at"),
        F.col("retrieved_at").cast("string").alias("retrieved_at"),
        F.col("source_page_url").cast("string").alias("source_page_url"),
        F.col("source_data_url").cast("string").alias("source_data_url"),
        F.col("source_raw_file").cast("string").alias("source_raw_file"),
        F.col("source_sha256").cast("string").alias("source_sha256"),
        F.col("payload_size_bytes").cast("long").alias("payload_size_bytes"),
        F.col("text").cast("string").alias("text"),
        F.col("html").cast("string").alias("html"),
        F.col("raw_xml").cast("string").alias("raw_xml"),
        F.col("source_file").cast("string").alias("source_file"),
        F.current_timestamp().alias("ingested_at"),
    )

    duplicate_document_ids = (
        df_bronze.groupBy("document_id")
        .agg(F.count("*").alias("row_count"))
        .where(F.col("row_count") > 1)
        .count()
    )
    if duplicate_document_ids:
        raise ValueError(
            f"Bronze contains {duplicate_document_ids} duplicate document IDs"
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
                    "unexpected_rows_pk": ["document_snapshot_id"],
                    "fail_on_error": True,
                    "dq_functions": [
                        {
                            "function": "expect_column_values_to_not_be_null",
                            "args": {"column": "document_snapshot_id"},
                        },
                        {
                            "function": "expect_column_values_to_be_unique",
                            "args": {"column": "document_snapshot_id"},
                        },
                        {
                            "function": "expect_table_row_count_to_be_between",
                            "args": {
                                "min_value": EXPECTED_DOCUMENT_COUNT,
                                "max_value": EXPECTED_DOCUMENT_COUNT,
                            },
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
        f"BRONZE | rows {df_source.count()} -> {df_bronze.count()} laws | "
        "added: snapshot ID, source file, ingestion time | output: Delta"
    )
    if PREVIEW:
        df_bronze.select(
            "document_id", "title", "version", "payload_size_bytes"
        ).show(10, truncate=64)
