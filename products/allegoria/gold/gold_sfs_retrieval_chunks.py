# Databricks notebook source
# MAGIC %pip install "lakehouse-engine[dq]==2.1.1"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

"""Prepare source-faithful SFS chunks for Databricks AI Search."""

import sys
from os import getenv
from pathlib import Path

from lakehouse_engine.engine import load_data
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

PROJECT_ROOT = Path.cwd().parents[2]
CHUNKER_FILE = PROJECT_ROOT / "products/allegoria/retrieval_chunks.py"
if not CHUNKER_FILE.is_file():
    raise FileNotFoundError(
        f"Retrieval chunker not found at {CHUNKER_FILE}. Run this notebook from "
        "its Databricks Git folder."
    )
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from products.allegoria.retrieval_chunks import (
    AI_SEARCH_MAX_SOURCE_BYTES,
    CHUNKING_STRATEGY,
    MAX_RETRIEVAL_CHARS,
    build_chunk_part_records,
)

CATALOG = getenv("ALLEGORIA_CATALOG", "dev_lakehouse")
DQ_ROOT = getenv("ALLEGORIA_DQ_ROOT", "/tmp/allegoria/dq")
PREVIEW = getenv("ALLEGORIA_PREVIEW", "true").lower() == "true"
SILVER_TABLE = f"{CATALOG}.silver_allegoria.sfs_provisions"
GOLD_TABLE = f"{CATALOG}.gold_allegoria.sfs_retrieval_chunks"
EXPECTED_PROVISION_COUNT = 1_952
EXPECTED_CHUNK_COUNT = 1_967

CHUNK_PART_SCHEMA = StructType(
    [
        StructField("provision_id", StringType(), False),
        StructField("part", IntegerType(), False),
        StructField("part_count", IntegerType(), False),
        StructField("retrieval_context", StringType(), False),
        StructField("content", StringType(), False),
    ]
)

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
    if df_silver.count() != EXPECTED_PROVISION_COUNT:
        raise ValueError(
            f"Retrieval chunks expect {EXPECTED_PROVISION_COUNT} Silver provisions"
        )

    source_rows = df_silver.select(
        "provision_id",
        "document_title",
        "chapter",
        "heading",
        "label",
        "text",
    ).collect()
    chunk_part_records = [
        chunk_part
        for row in source_rows
        for chunk_part in build_chunk_part_records(
            row.provision_id,
            row.document_title,
            row.chapter,
            row.heading,
            row.label,
            row.text,
        )
    ]
    if len(chunk_part_records) != EXPECTED_CHUNK_COUNT:
        raise ValueError(
            f"Retrieval chunks expect {EXPECTED_CHUNK_COUNT} rows, got "
            f"{len(chunk_part_records)}"
        )

    df_chunk_parts = spark.createDataFrame(
        chunk_part_records,
        schema=CHUNK_PART_SCHEMA,
    )
    df_chunk_source = df_chunk_parts.join(
        df_silver,
        on="provision_id",
        how="left",
    )
    df_with_retrieval_text = df_chunk_source.withColumn(
        "retrieval_text",
        F.concat_ws("\n\n", "retrieval_context", "content"),
    )

    df_chunks = df_with_retrieval_text.select(
        F.concat(
            F.col("provision_id"),
            F.lit(":chunk-"),
            F.lpad(F.col("part"), 2, "0"),
        ).alias("chunk_id"),
        F.col("document_snapshot_id"),
        F.col("document_id"),
        F.col("provision_id"),
        F.col("provision_text_sha256"),
        F.col("kind"),
        F.col("source_anchor"),
        F.col("source_anchor_occurrence"),
        F.col("label"),
        F.col("chapter"),
        F.col("heading"),
        F.col("order").alias("provision_order"),
        F.col("part"),
        F.col("part_count"),
        F.col("content"),
        F.length("content").cast("int").alias("content_char_count"),
        F.sha2("content", 256).alias("chunk_text_sha256"),
        F.col("retrieval_text"),
        F.length("retrieval_text").cast("int").alias("retrieval_char_count"),
        F.length(F.encode("retrieval_text", "UTF-8"))
        .cast("int")
        .alias("retrieval_byte_count"),
        F.col("document_title"),
        F.col("document_version"),
        F.col("source_url"),
        F.col("source_page_url"),
        F.col("source_sha256"),
        F.col("bronze_ingested_at"),
        F.col("silver_transformed_at"),
        F.lit(CHUNKING_STRATEGY).alias("chunking_strategy"),
        F.current_timestamp().alias("gold_prepared_at"),
    )

    missing_lineage = df_chunks.where(F.col("source_sha256").isNull()).count()
    oversized_chars = df_chunks.where(
        F.col("retrieval_char_count") > MAX_RETRIEVAL_CHARS
    ).count()
    oversized_bytes = df_chunks.where(
        F.col("retrieval_byte_count") > AI_SEARCH_MAX_SOURCE_BYTES
    ).count()
    duplicate_chunks = (
        df_chunks.groupBy("chunk_id")
        .agg(F.count("*").alias("row_count"))
        .where(F.col("row_count") > 1)
        .count()
    )
    if missing_lineage or oversized_chars or oversized_bytes or duplicate_chunks:
        raise ValueError(
            "Retrieval chunk validation failed: "
            f"missing_lineage={missing_lineage}, oversized_chars={oversized_chars}, "
            f"oversized_bytes={oversized_bytes}, duplicate_chunks={duplicate_chunks}"
        )

    df_reconstructed = (
        df_chunks.groupBy("provision_id")
        .agg(F.sort_array(F.collect_list(F.struct("part", "content"))).alias("parts"))
        .select(
            "provision_id",
            F.concat_ws(
                "\n\n",
                F.transform("parts", lambda part: part["content"]),
            ).alias("reconstructed_text"),
        )
    )
    reconstruction_errors = (
        df_silver.select("provision_id", F.col("text").alias("silver_text"))
        .join(df_reconstructed, on="provision_id", how="left")
        .where(
            F.col("reconstructed_text").isNull()
            | (F.col("reconstructed_text") != F.col("silver_text"))
        )
        .count()
    )
    if reconstruction_errors:
        raise ValueError(
            f"Retrieval chunks cannot reconstruct {reconstruction_errors} provisions"
        )

    load_data(
        acon={
            "input_specs": [
                {
                    "spec_id": "retrieval_chunks",
                    "read_type": "batch",
                    "data_format": "dataframe",
                    "df_name": df_chunks,
                }
            ],
            "dq_specs": [
                {
                    "spec_id": "retrieval_chunk_quality",
                    "input_id": "retrieval_chunks",
                    "dq_type": "validator",
                    "store_backend": "file_system",
                    "local_fs_root_dir": f"{DQ_ROOT}/gold_retrieval_chunks",
                    "unexpected_rows_pk": ["chunk_id"],
                    "fail_on_error": True,
                    "dq_functions": [
                        {
                            "function": "expect_column_values_to_not_be_null",
                            "args": {"column": "chunk_id"},
                        },
                        {
                            "function": "expect_column_values_to_be_unique",
                            "args": {"column": "chunk_id"},
                        },
                        {
                            "function": "expect_table_row_count_to_be_between",
                            "args": {
                                "min_value": EXPECTED_CHUNK_COUNT,
                                "max_value": EXPECTED_CHUNK_COUNT,
                            },
                        },
                    ],
                }
            ],
            "output_specs": [
                {
                    "spec_id": "retrieval_chunk_output",
                    "input_id": "retrieval_chunk_quality",
                    "write_type": "overwrite",
                    "data_format": "delta",
                    "db_table": GOLD_TABLE,
                    "options": {"overwriteSchema": "true"},
                }
            ],
        }
    )
    spark.sql(
        f"ALTER TABLE {GOLD_TABLE} SET TBLPROPERTIES "
        "(delta.enableChangeDataFeed = true)"
    )

    print(
        f"GOLD RETRIEVAL | rows {df_silver.count()} provisions -> "
        f"{df_chunks.count()} chunks | changed: long provisions split at logical "
        "blocks, retrieval context added | output: Delta"
    )
    if PREVIEW:
        df_chunks.select(
            "chunk_id",
            "document_id",
            "label",
            "part",
            "part_count",
            "retrieval_char_count",
        ).show(10, truncate=64)
