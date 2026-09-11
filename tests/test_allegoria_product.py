import ast
import hashlib
import json
from pathlib import Path

import yaml

from products.allegoria.retrieval_chunks import (
    MAX_RETRIEVAL_CHARS,
    build_retrieval_context,
    split_legal_content,
)
from products.allegoria.sfs_ingestion import (
    SEED_DOCUMENT_IDS,
    TARGET_DOCUMENT_COUNT,
    parse_sfs_xml,
)
from products.allegoria.sfs_parser import parse_sfs_html

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/allegoria"
SFS_SOURCE = ROOT / "data/source/sfs"
SFS_BRONZE = ROOT / "data/bronze/sfs"
LAS_BRONZE = SFS_BRONZE / "sfs-1982-80.json"
LAS_SOURCE = SFS_SOURCE / "sfs-1982-80.xml"
EXPECTED_LAS_SHA256 = (
    "a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b"
)
EXPECTED_PROVISION_COUNT = 1952
EXPECTED_CHUNK_COUNT = 1967
NOTEBOOKS = (
    PRODUCT / "setup/setup_catalog.py",
    PRODUCT / "bronze/bronze_sfs.py",
    PRODUCT / "silver/silver_sfs.py",
    PRODUCT / "gold/gold_sfs.py",
    PRODUCT / "gold/gold_sfs_retrieval_chunks.py",
)


def test_las_regression_fixture() -> None:
    assert hashlib.sha256(LAS_SOURCE.read_bytes()).hexdigest() == EXPECTED_LAS_SHA256

    bronze = json.loads(LAS_BRONZE.read_text(encoding="utf-8"))
    assert bronze["document_id"] == "sfs-1982-80"
    assert bronze["source_sha256"] == EXPECTED_LAS_SHA256

    provisions = parse_sfs_html(bronze["html"], bronze["document_id"])
    paragraph_count = sum(row["kind"] == "paragraph" for row in provisions)
    transition_count = sum(
        row["kind"] == "transitional_provision" for row in provisions
    )

    assert len(provisions) == 92
    assert paragraph_count == 70
    assert transition_count == 22
    assert provisions[0]["provision_suffix"] == "P1"
    assert provisions[-1]["label"] == "SFS 2022:835"


def test_50_law_corpus_matches_raw_api_responses() -> None:
    manifest = json.loads((SFS_SOURCE / "manifest.json").read_text(encoding="utf-8"))
    manifest_documents = manifest["documents"]
    document_ids = tuple(item["document_id"] for item in manifest_documents)

    assert manifest["selection"]["target_count"] == TARGET_DOCUMENT_COUNT
    assert document_ids[: len(SEED_DOCUMENT_IDS)] == SEED_DOCUMENT_IDS
    assert len(document_ids) == len(set(document_ids)) == TARGET_DOCUMENT_COUNT
    assert len(list(SFS_SOURCE.glob("*.xml"))) == TARGET_DOCUMENT_COUNT
    assert len(list(SFS_BRONZE.glob("*.json"))) == TARGET_DOCUMENT_COUNT

    for item in manifest_documents:
        document_id = item["document_id"]
        raw_xml = (SFS_SOURCE / item["raw_file"]).read_bytes()
        bronze = json.loads(
            (SFS_BRONZE / f"{document_id}.json").read_text(encoding="utf-8")
        )
        raw_sha256 = hashlib.sha256(raw_xml).hexdigest()

        assert item["raw_sha256"] == raw_sha256 == bronze["source_sha256"]
        assert bronze["raw_xml"].encode("utf-8") == raw_xml
        assert bronze["document_snapshot_id"] == f"{document_id}:{raw_sha256}"
        assert "förordning" not in bronze["title"].casefold()
        assert parse_sfs_xml(
            raw_xml,
            document_id,
            bronze["source_data_url"],
            bronze["retrieved_at"],
        ) == bronze


def test_all_50_laws_parse_into_provisions() -> None:
    provision_count = 0
    parsed_document_ids: set[str] = set()

    for source_file in sorted(SFS_BRONZE.glob("*.json")):
        bronze = json.loads(source_file.read_text(encoding="utf-8"))
        provisions = parse_sfs_html(bronze["html"], bronze["document_id"])
        assert provisions
        assert {row["document_id"] for row in provisions} == {bronze["document_id"]}
        assert len({row["provision_suffix"] for row in provisions}) == len(provisions)
        provision_count += len(provisions)
        parsed_document_ids.add(bronze["document_id"])

    assert len(parsed_document_ids) == TARGET_DOCUMENT_COUNT
    assert provision_count == EXPECTED_PROVISION_COUNT


def test_retrieval_chunks_preserve_every_provision() -> None:
    chunk_count = 0
    split_provision_count = 0
    largest_retrieval_text = 0

    for source_file in sorted(SFS_BRONZE.glob("*.json")):
        bronze = json.loads(source_file.read_text(encoding="utf-8"))
        provisions = parse_sfs_html(bronze["html"], bronze["document_id"])

        for provision in provisions:
            context = build_retrieval_context(
                bronze["title"],
                provision["chapter"],
                provision["heading"],
                provision["label"],
            )
            parts = split_legal_content(provision["text"], context)

            assert "\n\n".join(parts) == provision["text"]
            assert all(
                len(f"{context}\n\n{part}") <= MAX_RETRIEVAL_CHARS
                for part in parts
            )

            chunk_count += len(parts)
            split_provision_count += len(parts) > 1
            largest_retrieval_text = max(
                largest_retrieval_text,
                *(len(f"{context}\n\n{part}") for part in parts),
            )

    assert chunk_count == EXPECTED_CHUNK_COUNT
    assert split_provision_count == 11
    assert largest_retrieval_text == 1997


def test_chunking_fails_for_an_oversized_indivisible_block() -> None:
    context = "Lag (1982:80) om anställningsskydd"
    oversized_block = "x" * MAX_RETRIEVAL_CHARS

    try:
        split_legal_content(oversized_block, context)
    except ValueError as error:
        assert "indivisible legal text block" in str(error)
    else:
        raise AssertionError("Oversized indivisible content must fail")


def test_notebooks_are_small_valid_and_explain_their_change() -> None:
    for notebook in NOTEBOOKS:
        source = notebook.read_text(encoding="utf-8")
        ast.parse(source)
        assert len(source.splitlines()) <= 300

    for notebook in NOTEBOOKS[1:]:
        source = notebook.read_text(encoding="utf-8")
        assert '# MAGIC %pip install "lakehouse-engine[dq]==2.1.1"' in source
        assert "dbutils.library.restartPython()" in source
        assert "from pyspark.sql" in source
        assert "load_data" in source
        assert "print(" in source
        assert "rows" in source
        assert "output: Delta" in source

    bronze_source = NOTEBOOKS[1].read_text(encoding="utf-8")
    silver_source = NOTEBOOKS[2].read_text(encoding="utf-8")
    assert "data/bronze/sfs" in bronze_source
    assert "sfs_documents" in bronze_source
    assert "sfs_provisions" in silver_source
    assert '"beautifulsoup4==4.13.5"' in silver_source
    assert "Path(__file__)" not in bronze_source
    assert "Path(__file__)" not in silver_source
    assert 'F.sha2("raw_xml", 256)' in bronze_source
    assert 'record["source_file"]' not in bronze_source
    assert 'alias("bronze_ingested_at")' in bronze_source
    assert 'F.col("ingested_at").alias("bronze_ingested_at")' in silver_source


def test_bundle_orders_setup_bronze_silver_gold() -> None:
    bundle = yaml.safe_load((ROOT / "databricks.yml").read_text(encoding="utf-8"))
    job = bundle["resources"]["jobs"]["allegoria_sfs_medallion"]
    tasks = {task["task_key"]: task for task in job["tasks"]}

    assert set(tasks) == {
        "setup_catalog",
        "bronze_sfs",
        "silver_sfs",
        "gold_sfs",
        "gold_sfs_retrieval_chunks",
    }
    assert tasks["bronze_sfs"]["depends_on"] == [{"task_key": "setup_catalog"}]
    assert tasks["silver_sfs"]["depends_on"] == [{"task_key": "bronze_sfs"}]
    assert tasks["gold_sfs"]["depends_on"] == [{"task_key": "silver_sfs"}]
    assert tasks["gold_sfs_retrieval_chunks"]["depends_on"] == [
        {"task_key": "silver_sfs"}
    ]
    assert bundle["variables"]["catalog"]["default"] == "dev_lakehouse"


def test_product_boundaries_are_explicit() -> None:
    allegoria_readme = (PRODUCT / "README.md").read_text(encoding="utf-8")

    assert "bronze_allegoria.sfs_documents" in allegoria_readme
    assert "silver_allegoria.sfs_provisions" in allegoria_readme
    assert "gold_allegoria.sfs_provision_summary" in allegoria_readme
    assert "gold_allegoria.sfs_retrieval_chunks" in allegoria_readme


def test_measurement_does_not_import_selection() -> None:
    """The boundary that matters, checked structurally rather than in prose.

    `DIRECTION.md` assigns slot annotation to human hands because it decides the
    sign. A selection heuristic reaching into the metric would arrive as an
    ordinary-looking import, so the rule is enforced here rather than trusted to
    a docstring. This previously asserted phrases in a README, which could not
    fail for the right reason.
    """
    offenders: list[str] = []
    for path in sorted((ROOT / "simulacria/measurement").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "simulacria.selection"
            ):
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: from {node.module}")
            elif isinstance(node, ast.Import):
                offenders += [
                    f"{path.relative_to(ROOT)}:{node.lineno}: import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith("simulacria.selection")
                ]

    assert not offenders, "simulacria.measurement must not import from simulacria.selection: " + (
        "; ".join(offenders)
    )
