import ast
import hashlib
import json
from pathlib import Path

import yaml

from products.allegoria.source_parser import parse_las_html

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/allegoria"
BRONZE_JSON = ROOT / "data/bronze/las/sfs-1982-80.json"
SOURCE_XML = ROOT / "data/source/las/sfs-1982-80.xml"
EXPECTED_SHA256 = "a310dbc84411b7a7cfa7fc29bd0f52306e2b4358407ac84f74363a8aa5db2f9b"
NOTEBOOKS = (
    PRODUCT / "setup_allegoria/notebook.py",
    PRODUCT / "bronze_allegoria/notebook.py",
    PRODUCT / "silver_allegoria/notebook.py",
    PRODUCT / "gold_allegoria/notebook.py",
)


def test_source_snapshot_and_parser_contract() -> None:
    assert hashlib.sha256(SOURCE_XML.read_bytes()).hexdigest() == EXPECTED_SHA256

    bronze = json.loads(BRONZE_JSON.read_text(encoding="utf-8"))
    assert bronze["document_id"] == "sfs-1982-80"
    assert bronze["source_sha256"] == EXPECTED_SHA256

    provisions = parse_las_html(bronze["html"], bronze["document_id"])
    paragraph_count = sum(row["kind"] == "paragraph" for row in provisions)
    transition_count = sum(
        row["kind"] == "transitional_provision" for row in provisions
    )

    assert len(provisions) == 92
    assert paragraph_count == 70
    assert transition_count == 22
    assert len({(row["kind"], row["heading"]) for row in provisions}) == 19
    assert provisions[0]["provision_suffix"] == "P1"
    assert provisions[-1]["label"] == "SFS 2022:835"


def test_notebooks_are_small_valid_and_explain_their_change() -> None:
    for notebook in NOTEBOOKS:
        source = notebook.read_text(encoding="utf-8")
        ast.parse(source)
        assert len(source.splitlines()) <= 300

    for notebook in NOTEBOOKS[1:]:
        source = notebook.read_text(encoding="utf-8")
        assert "from pyspark.sql" in source
        assert "load_data" in source
        assert "print(" in source
        assert "rows" in source
        assert "output: Delta" in source


def test_bundle_orders_setup_bronze_silver_gold() -> None:
    bundle = yaml.safe_load((ROOT / "databricks.yml").read_text(encoding="utf-8"))
    job = bundle["resources"]["jobs"]["allegoria_medallion"]
    tasks = {task["task_key"]: task for task in job["tasks"]}

    assert set(tasks) == {"setup", "bronze", "silver", "gold"}
    assert tasks["bronze"]["depends_on"] == [{"task_key": "setup"}]
    assert tasks["silver"]["depends_on"] == [{"task_key": "bronze"}]
    assert tasks["gold"]["depends_on"] == [{"task_key": "silver"}]
    assert bundle["variables"]["catalog"]["default"] == "dev_lakehouse"

    packages = [
        library["pypi"]["package"]
        for task in tasks.values()
        for library in task.get("libraries", [])
    ]
    assert packages.count("lakehouse-engine[dq]==2.1.1") == 3
    assert "beautifulsoup4==4.13.5" in packages


def test_product_boundaries_are_explicit() -> None:
    allegoria_readme = (PRODUCT / "README.md").read_text(encoding="utf-8")
    simulacria_readme = (
        ROOT / "products/simulacria/README.md"
    ).read_text(encoding="utf-8")

    assert "bronze_allegoria.las_documents" in allegoria_readme
    assert "silver_allegoria.las_provisions" in allegoria_readme
    assert "gold_allegoria.provision_summary" in allegoria_readme
    assert "no executable pipeline yet" in simulacria_readme
