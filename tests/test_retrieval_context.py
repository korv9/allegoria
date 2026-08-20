import json
import unittest

import pandas as pd

from backend.retrieval import (
    LexicalRetriever,
    build_context_packet,
    format_context_text,
    load_gold_df,
)


class RetrievalContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        gold_df = load_gold_df()
        with LexicalRetriever(gold_df) as retriever:
            cls.result_df = retriever.search(
                "sakliga skäl uppsägning",
                top_k=3,
            )

    def test_builds_serializable_source_traceable_packet(self) -> None:
        packet = build_context_packet(
            query="sakliga skäl uppsägning",
            retriever="sqlite_fts5_bm25",
            result_df=self.result_df,
        )

        json.dumps(packet, ensure_ascii=False, allow_nan=False)
        self.assertEqual(packet["schema_version"], "1.0")
        self.assertEqual(packet["chunk_count"], 3)
        first_chunk = packet["chunks"][0]
        self.assertEqual(first_chunk["citation_id"], "source-01")
        self.assertEqual(first_chunk["provision_id"], "sfs-1982-80:P7")
        self.assertTrue(first_chunk["source_url"].endswith("#P7"))
        self.assertEqual(len(first_chunk["source_sha256"]), 64)

    def test_formats_prompt_ready_context_without_changing_content(self) -> None:
        packet = build_context_packet(
            query="sakliga skäl uppsägning",
            retriever="sqlite_fts5_bm25",
            result_df=self.result_df,
        )
        context_text = format_context_text(packet)

        self.assertIn("[source-01]", context_text)
        self.assertIn("provision_id: sfs-1982-80:P7", context_text)
        self.assertIn(self.result_df.iloc[0]["content"], context_text)
        self.assertIn(self.result_df.iloc[0]["source_url"], context_text)

    def test_rejects_empty_retrieval_results(self) -> None:
        with self.assertRaisesRegex(ValueError, "without retrieved chunks"):
            build_context_packet(
                query="fråga",
                retriever="sqlite_fts5_bm25",
                result_df=pd.DataFrame(),
            )

    def test_rejects_non_consecutive_ranks(self) -> None:
        invalid_df = self.result_df.copy()
        invalid_df.loc[invalid_df.index[0], "rank"] = 2

        with self.assertRaisesRegex(ValueError, "consecutive"):
            build_context_packet(
                query="fråga",
                retriever="sqlite_fts5_bm25",
                result_df=invalid_df,
            )
