import unittest

from backend.ingestion import LAS_SOURCE_PATH, load_las


class LoadLasTests(unittest.TestCase):
    def test_loads_the_canonical_las_source(self) -> None:
        source = load_las()

        self.assertEqual(source.document_id, "sfs-1982-80")
        self.assertEqual(source.title, "Lag (1982:80) om anställningsskydd")
        self.assertEqual(source.version, "t.o.m. SFS 2022:836")
        self.assertEqual(
            source.raw_sha256,
            "a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b",
        )
        self.assertEqual(source.raw_path, LAS_SOURCE_PATH)
        self.assertTrue(source.text.startswith("Inledande bestämmelser\n\n1 §"))
        self.assertIn("Övergångsbestämmelser", source.text)
        self.assertEqual(len(source.text), 57_372)
        self.assertIn('class="paragraf"', source.html)



if __name__ == "__main__":
    unittest.main()
