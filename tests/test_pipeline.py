import json
import tempfile
import unittest
from pathlib import Path

from backend.lakehouse.bronze import BRONZE_PATH, build_bronze_df, write_bronze_df
from backend.lakehouse.gold import GOLD_PATH, build_gold_df, write_gold_df
from backend.lakehouse.quality import (
    QUALITY_PATH,
    build_quality_df,
    write_quality_df,
)
from backend.lakehouse.silver import SILVER_PATH, build_silver_df, write_silver_df


class PipelineArtifactTests(unittest.TestCase):
    def test_committed_artifacts_are_reproducible(self) -> None:
        bronze_df = build_bronze_df()
        silver_df = build_silver_df(bronze_df)
        gold_df = build_gold_df(bronze_df, silver_df)
        quality_df = build_quality_df(silver_df, gold_df)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bronze_path = root / "bronze.json"
            silver_path = root / "silver.jsonl"
            gold_path = root / "gold.jsonl"
            quality_path = root / "quality.jsonl"
            write_bronze_df(bronze_df, bronze_path)
            write_silver_df(silver_df, silver_path)
            write_gold_df(gold_df, gold_path)
            write_quality_df(quality_df, quality_path)

            self.assertEqual(bronze_path.read_bytes(), BRONZE_PATH.read_bytes())
            self.assertEqual(silver_path.read_bytes(), SILVER_PATH.read_bytes())
            self.assertEqual(gold_path.read_bytes(), GOLD_PATH.read_bytes())
            self.assertEqual(quality_path.read_bytes(), QUALITY_PATH.read_bytes())

        self.assertEqual(json.loads(BRONZE_PATH.read_text())["document_id"], "sfs-1982-80")
