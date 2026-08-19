import unittest

from backend.retrieval.evaluation import evaluate_las


class RetrievalEvaluationTests(unittest.TestCase):
    def test_measures_known_lexical_strengths_and_limitations(self) -> None:
        result_df, summary_df = evaluate_las(top_k=3)

        summary = summary_df.iloc[0]
        missed_queries = result_df.loc[~result_df["hit"], "query_id"].tolist()

        self.assertEqual(summary["query_count"], 7)
        self.assertEqual(summary["hit_count"], 6)
        self.assertAlmostEqual(summary["hit_rate"], 6 / 7)
        self.assertEqual(missed_queries, ["las-007"])
