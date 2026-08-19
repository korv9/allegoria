import json
import tempfile
import unittest
from pathlib import Path

from backend.lakehouse.bronze import build_bronze_df
from backend.lakehouse.gold import MAX_RETRIEVAL_CHARS, build_gold_df, write_gold_df
from backend.lakehouse.silver import build_silver_df


class GoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bronze_df = build_bronze_df()
        cls.silver_df = build_silver_df(cls.bronze_df)
        cls.gold_df = build_gold_df(cls.bronze_df, cls.silver_df)

    def test_every_provision_has_retrieval_chunks(self) -> None:
        represented = set(self.gold_df["provision_id"])
        expected = set(self.silver_df["provision_id"])

        self.assertEqual(len(self.gold_df), 96)
        self.assertEqual(represented, expected)

    def test_chunks_respect_the_documented_size_limit(self) -> None:
        self.assertTrue(
            (self.gold_df["retrieval_char_count"] <= MAX_RETRIEVAL_CHARS).all()
        )
        self.assertEqual(str(self.gold_df["part"].dtype), "int64")
        self.assertEqual(str(self.gold_df["retrieval_char_count"].dtype), "int64")

    def test_chunk_content_reconstructs_every_silver_provision(self) -> None:
        reconstructed = (
            self.gold_df.sort_values(["provision_id", "part"])
            .groupby("provision_id", sort=False)["content"]
            .agg("\n\n".join)
        )
        expected = self.silver_df.set_index("provision_id")["text"]

        self.assertEqual(reconstructed.to_dict(), expected.to_dict())

    def test_serialization_is_one_json_record_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.jsonl"
            write_gold_df(self.gold_df, path)
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(records), len(self.gold_df))
        self.assertEqual(records[0]["chunk_id"], "sfs-1982-80:P1:chunk-01")
