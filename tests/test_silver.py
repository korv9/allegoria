import json
import tempfile
import unittest
from pathlib import Path

from backend.lakehouse.bronze import build_bronze_df
from backend.lakehouse.silver import build_silver_df, write_silver_df


class SilverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.silver_df = build_silver_df(build_bronze_df())

    def test_extracts_all_source_paragraph_anchors(self) -> None:
        paragraphs_df = self.silver_df[self.silver_df["kind"] == "paragraph"]

        self.assertEqual(len(paragraphs_df), 70)
        self.assertEqual(paragraphs_df["provision_id"].nunique(), 70)
        self.assertEqual(str(self.silver_df["order"].dtype), "int64")

    def test_preserves_stable_source_lineage(self) -> None:
        paragraph = self.silver_df.loc[
            self.silver_df["provision_id"] == "sfs-1982-80:P7"
        ].iloc[0]

        self.assertEqual(paragraph["label"], "7 §")
        self.assertEqual(paragraph["heading"], "Uppsägning från arbetsgivarens sida")
        self.assertTrue(paragraph["text"].startswith("Uppsägning från arbetsgivarens sida"))
        self.assertTrue(paragraph["source_url"].endswith("#P7"))

    def test_separates_transitional_provisions_from_section_43(self) -> None:
        section_43 = self.silver_df.loc[
            self.silver_df["provision_id"] == "sfs-1982-80:P43"
        ].iloc[0]
        transitions_df = self.silver_df[
            self.silver_df["kind"] == "transitional_provision"
        ]

        self.assertLess(len(section_43["text"]), 1_000)
        self.assertEqual(len(transitions_df), 22)
        self.assertEqual(
            transitions_df.iloc[0]["provision_id"],
            "sfs-1982-80:overgang:1984-510",
        )
        self.assertTrue(transitions_df.iloc[0]["text"].startswith("1984:510"))
        self.assertEqual(transitions_df.iloc[-1]["label"], "SFS 2022:835")

    def test_serialization_is_one_json_record_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "silver.jsonl"
            write_silver_df(self.silver_df, path)
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(records), 92)
        self.assertEqual(records[0]["provision_id"], "sfs-1982-80:P1")
