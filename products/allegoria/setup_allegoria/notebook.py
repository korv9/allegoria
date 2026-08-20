# Databricks notebook source
"""Create the Unity Catalog objects required by the Allegoria medallion flow."""

import re
from os import getenv

CATALOG = getenv("ALLEGORIA_CATALOG", "dev_lakehouse")
SCHEMAS = ("bronze_allegoria", "silver_allegoria", "gold_allegoria")

if __name__ == "__main__":
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", CATALOG):
        raise ValueError(f"Invalid Unity Catalog identifier: {CATALOG}")

    spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
    for schema in SCHEMAS:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}")

    print(f"SETUP | catalog: {CATALOG} | schemas: {', '.join(SCHEMAS)}")
