import unittest

import pandas as pd

from backend.retrieval import load_gold_df
from backend.retrieval.evaluation import (
    evaluate_las,
    load_evaluation_df,
    summarize_evaluation_by_query_type,
    validate_relevance_labels,
)


class RetrievalEvaluationTests(unittest.TestCase):
    def test_measures_known_lexical_strengths_and_limitations(self) -> None:
        result_df, summary_df = evaluate_las(top_k=3)

        summary = summary_df.iloc[0]
        missed_queries = result_df.loc[~result_df["hit"], "query_id"].tolist()

        self.assertEqual(summary["query_count"], 30)
        self.assertEqual(summary["hit_count"], 26)
        self.assertAlmostEqual(summary["hit_rate"], 26 / 30)
        self.assertAlmostEqual(summary["mean_reciprocal_rank"], 23 / 30)
        self.assertEqual(
            missed_queries,
            ["las-007", "las-012", "las-014", "las-030"],
        )

    def test_reports_legal_and_natural_language_separately(self) -> None:
        result_df, _ = evaluate_las(top_k=3)
        summary_df = summarize_evaluation_by_query_type(result_df)

        self.assertEqual(
            set(summary_df["query_type"]),
            {"legal_terms", "natural_language"},
        )
        self.assertEqual(summary_df["query_count"].sum(), 30)

        by_type = summary_df.set_index("query_type")
        self.assertEqual(by_type.loc["legal_terms", "query_count"], 14)
        self.assertEqual(by_type.loc["legal_terms", "hit_count"], 14)
        self.assertEqual(by_type.loc["natural_language", "query_count"], 16)
        self.assertEqual(by_type.loc["natural_language", "hit_count"], 12)

    def test_all_relevance_labels_exist_in_gold(self) -> None:
        validate_relevance_labels(load_evaluation_df(), load_gold_df())

    def test_rejects_unknown_relevance_label(self) -> None:
        evaluation_df = load_evaluation_df().head(1).copy()
        evaluation_df.at[0, "relevant_provision_ids"] = ["unknown:P999"]

        with self.assertRaisesRegex(ValueError, "unknown provision IDs"):
            validate_relevance_labels(evaluation_df, load_gold_df())
