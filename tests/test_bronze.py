import json
import tempfile
import unittest
from pathlib import Path

from backend.lakehouse.bronze import BRONZE_DTYPES, build_bronze_df, write_bronze_df


class BronzeTests(unittest.TestCase):
    def test_preserves_las_document_and_provenance(self) -> None:
        bronze_df = build_bronze_df()
        document = bronze_df.iloc[0]

        self.assertEqual(document["document_id"], "sfs-1982-80")
        self.assertEqual(document["version"], "t.o.m. SFS 2022:836")
        self.assertEqual(len(document["text"]), 57_372)
        self.assertIn('class="paragraf"', document["html"])
        self.assertEqual(
            {column: str(dtype) for column, dtype in bronze_df.dtypes.items()},
            BRONZE_DTYPES,
        )

    def test_serialization_is_utf8_json(self) -> None:
        bronze_df = build_bronze_df()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bronze.json"
            write_bronze_df(bronze_df, path)
            serialized = json.loads(path.read_text(encoding="utf-8"))

        document = bronze_df.iloc[0]
        self.assertEqual(serialized["document_id"], document["document_id"])
        self.assertEqual(serialized["text"], document["text"])
        self.assertEqual(serialized["html"], document["html"])
