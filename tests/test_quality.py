import unittest

from backend.lakehouse.bronze import build_bronze_df
from backend.lakehouse.gold import build_gold_df
from backend.lakehouse.quality import build_quality_df, validate_las_data
from backend.lakehouse.silver import build_silver_df


class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        bronze_df = build_bronze_df()
        silver_df = build_silver_df(bronze_df)
        gold_df = build_gold_df(bronze_df, silver_df)
        cls.bronze_df = bronze_df
        cls.silver_df = silver_df
        cls.gold_df = gold_df
        cls.quality_df = build_quality_df(silver_df, gold_df)

    def test_profiles_silver_and_gold_by_provision_kind(self) -> None:
        paragraph = self.quality_df.loc[
            self.quality_df["kind"] == "paragraph"
        ].iloc[0]
        transitional = self.quality_df.loc[
            self.quality_df["kind"] == "transitional_provision"
        ].iloc[0]

        self.assertEqual(paragraph["provision_count"], 70)
        self.assertEqual(paragraph["chunk_count"], 73)
        self.assertEqual(transitional["provision_count"], 22)
        self.assertEqual(transitional["chunk_count"], 23)
        self.assertEqual(len(self.quality_df), 2)

    def test_accepts_complete_source_lineage(self) -> None:
        validate_las_data(self.bronze_df, self.silver_df, self.gold_df)

    def test_rejects_duplicate_silver_provision_ids(self) -> None:
        invalid_silver_df = self.silver_df.copy()
        invalid_silver_df.loc[1, "provision_id"] = invalid_silver_df.loc[
            0, "provision_id"
        ]

        with self.assertRaisesRegex(ValueError, "duplicate provision IDs"):
            validate_las_data(
                self.bronze_df,
                invalid_silver_df,
                self.gold_df,
            )

    def test_rejects_gold_with_missing_provision(self) -> None:
        missing_provision_id = self.silver_df.loc[0, "provision_id"]
        invalid_gold_df = self.gold_df.loc[
            self.gold_df["provision_id"] != missing_provision_id
        ]

        with self.assertRaisesRegex(ValueError, "represent all Silver provisions"):
            validate_las_data(
                self.bronze_df,
                self.silver_df,
                invalid_gold_df,
            )
