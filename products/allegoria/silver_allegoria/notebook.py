# Databricks notebook source
# MAGIC %pip install "lakehouse-engine[dq]==2.1.1" "beautifulsoup4==4.13.5"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

"""Parse the Bronze LAS document into typed, source-traceable legal provisions."""

import sys
from os import getenv
from pathlib import Path

from lakehouse_engine.engine import load_data
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

PROJECT_ROOT = Path.cwd().parents[2]
PARSER_FILE = PROJECT_ROOT / "products/allegoria/source_parser.py"
if not PARSER_FILE.is_file():
    raise FileNotFoundError(
        f"Allegoria parser not found at {PARSER_FILE}. Run this notebook from its "
        "Databricks Git folder."
    )
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from products.allegoria.source_parser import parse_las_html

CATALOG = getenv("ALLEGORIA_CATALOG", "dev_lakehouse")
DQ_ROOT = getenv("ALLEGORIA_DQ_ROOT", "/tmp/allegoria/dq")
PREVIEW = getenv("ALLEGORIA_PREVIEW", "true").lower() == "true"
BRONZE_TABLE = f"{CATALOG}.bronze_allegoria.las_documents"
SILVER_TABLE = f"{CATALOG}.silver_allegoria.las_provisions"

PARSED_SCHEMA = StructType(
    [
        StructField("document_id", StringType(), False),
        StructField("provision_suffix", StringType(), False),
        StructField("kind", StringType(), False),
        StructField("source_anchor", StringType(), False),
        StructField("label", StringType(), False),
        StructField("heading", StringType(), False),
        StructField("order", IntegerType(), False),
        StructField("text", StringType(), False),
        StructField("subsection_anchors", ArrayType(StringType()), False),
        StructField("amendment_notes", ArrayType(StringType()), False),
    ]
)

READ_ACON = {
    "input_specs": [
        {
            "spec_id": "bronze_table",
            "read_type": "batch",
            "data_format": "delta",
            "db_table": BRONZE_TABLE,
        }
    ],
    "output_specs": [
        {
            "spec_id": "bronze_documents",
            "input_id": "bronze_table",
            "data_format": "dataframe",
        }
    ],
}

if __name__ == "__main__":
    df_bronze = load_data(acon=READ_ACON)["bronze_documents"]
    bronze_documents = df_bronze.select("document_id", "html").collect()
    if len(bronze_documents) != 1:
        raise ValueError(
            f"Silver expects exactly one Bronze document, got {len(bronze_documents)}"
        )

    document = bronze_documents[0]
    parsed_records = parse_las_html(document.html, document.document_id)
    df_parsed = spark.createDataFrame(parsed_records, schema=PARSED_SCHEMA)

    df_document_metadata = df_bronze.select(
        "document_id",
        "title",
        "version",
        "source_page_url",
        "source_sha256",
        "ingested_at",
    )

    df_enriched = df_parsed.join(
        df_document_metadata,
        on="document_id",
        how="left",
    )

    df_silver = df_enriched.select(
        F.concat_ws(":", "document_id", "provision_suffix").alias("provision_id"),
        F.col("document_id").cast("string").alias("document_id"),
        F.col("kind").cast("string").alias("kind"),
        F.col("source_anchor").cast("string").alias("source_anchor"),
        F.col("label").cast("string").alias("label"),
        F.col("heading").cast("string").alias("heading"),
        F.col("order").cast("int").alias("order"),
        F.col("text").cast("string").alias("text"),
        F.col("subsection_anchors").cast("array<string>").alias("subsection_anchors"),
        F.col("amendment_notes").cast("array<string>").alias("amendment_notes"),
        F.col("title").cast("string").alias("document_title"),
        F.col("version").cast("string").alias("document_version"),
        F.concat_ws("#", "source_page_url", "source_anchor").alias("source_url"),
        F.col("source_page_url").cast("string").alias("source_page_url"),
        F.col("source_sha256").cast("string").alias("source_sha256"),
        F.col("ingested_at").alias("bronze_ingested_at"),
        F.current_timestamp().alias("silver_transformed_at"),
    )

    unmatched_rows = df_silver.where(F.col("source_sha256").isNull()).count()
    if unmatched_rows:
        raise ValueError(
            f"Silver left join produced {unmatched_rows} rows without Bronze lineage"
        )

    duplicate_ids = (
        df_silver.groupBy("provision_id")
        .agg(F.count("*").alias("row_count"))
        .where(F.col("row_count") > 1)
        .count()
    )
    if duplicate_ids:
        raise ValueError(f"Silver contains {duplicate_ids} duplicate provision IDs")

    load_data(
        acon={
            "input_specs": [
                {
                    "spec_id": "silver_provisions",
                    "read_type": "batch",
                    "data_format": "dataframe",
                    "df_name": df_silver,
                }
            ],
            "dq_specs": [
                {
                    "spec_id": "silver_quality",
                    "input_id": "silver_provisions",
                    "dq_type": "validator",
                    "store_backend": "file_system",
                    "local_fs_root_dir": f"{DQ_ROOT}/silver",
                    "unexpected_rows_pk": ["provision_id"],
                    "fail_on_error": True,
                    "dq_functions": [
                        {
                            "function": "expect_column_values_to_not_be_null",
                            "args": {"column": "provision_id"},
                        },
                        {
                            "function": "expect_column_values_to_be_unique",
                            "args": {"column": "provision_id"},
                        },
                        {
                            "function": "expect_table_row_count_to_be_between",
                            "args": {"min_value": 92, "max_value": 92},
                        },
                    ],
                }
            ],
            "output_specs": [
                {
                    "spec_id": "silver_output",
                    "input_id": "silver_quality",
                    "write_type": "overwrite",
                    "data_format": "delta",
                    "db_table": SILVER_TABLE,
                    "options": {"overwriteSchema": "true"},
                }
            ],
        }
    )

    print(
        f"SILVER | rows {df_bronze.count()} document -> {df_silver.count()} provisions | "
        "changed: HTML parsed, IDs created, Bronze lineage joined | output: Delta"
    )
    if PREVIEW:
        df_silver.select(
            "provision_id", "kind", "label", "heading", "order"
        ).show(5, truncate=48)
