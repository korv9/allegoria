import tempfile
import unittest
from pathlib import Path

from backend.retrieval import LexicalRetriever, load_gold_df


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold_df = load_gold_df()

    def test_loads_all_gold_chunks_with_explicit_types(self) -> None:
        self.assertEqual(len(self.gold_df), 96)
        self.assertEqual(str(self.gold_df["chunk_id"].dtype), "string")
        self.assertEqual(str(self.gold_df["part"].dtype), "int64")

    def test_returns_ranked_source_traceable_results(self) -> None:
        with LexicalRetriever(self.gold_df) as retriever:
            result_df = retriever.search("sakliga skäl uppsägning", top_k=3)

        first_result = result_df.iloc[0]
        self.assertEqual(first_result["rank"], 1)
        self.assertEqual(first_result["provision_id"], "sfs-1982-80:P7")
        self.assertTrue(first_result["source_url"].endswith("#P7"))
        self.assertEqual(
            first_result["source_sha256"],
            self.gold_df.iloc[0]["source_sha256"],
        )

    def test_returns_empty_dataframe_when_no_term_matches(self) -> None:
        with LexicalRetriever(self.gold_df) as retriever:
            result_df = retriever.search("qzxwvvnonexistent", top_k=3)

        self.assertTrue(result_df.empty)
        self.assertEqual(
            list(result_df.columns),
            [
                "rank",
                "score",
                "chunk_id",
                "document_id",
                "provision_id",
                "kind",
                "label",
                "heading",
                "part",
                "content",
                "retrieval_text",
                "source_url",
                "source_sha256",
            ],
        )

    def test_rejects_query_without_searchable_tokens(self) -> None:
        with LexicalRetriever(self.gold_df) as retriever:
            with self.assertRaisesRegex(ValueError, "at least one word"):
                retriever.search("---", top_k=3)

    def test_rejects_missing_gold_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "missing.jsonl"
            with self.assertRaises(FileNotFoundError):
                load_gold_df(missing_path)
