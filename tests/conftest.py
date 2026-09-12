"""A minimal but real experiment world in a temporary directory.

The run code reads an experiment config, a corpus and prompt files from disk.
Tests build tiny real ones instead of monkeypatching the loader, so the config
path itself stays covered: a corpus that stops loading, or a config field that
is renamed, fails a test rather than only failing a paid run.

Every text here is a fixture. Nothing in this file is experiment evidence.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
import yaml

TEXT = "vila"
SLOT = {
    "slot_id": "compensation",
    "kind": "condition",
    "attaches_to": "duty",
    "question": "Finns ett krav på kompensation?",
}


def write_experiment(root: Path, name: str = "pilot-sv", generations: int = 1) -> Path:
    """Write corpus, prompts, prediction and config under `root`; return the config path."""
    for folder in ("corpus", "configs", "prompts/test", "predictions"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "corpus/test_inline.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "domain": "inline",
                "corpus_version": "test_inline",
                "annotation_status": "assistant_draft_requires_human_review",
                "group": "test",
                "passages": [
                    {
                        "passage_id": "test-only",
                        "text": TEXT,
                        "text_sha256": sha256(TEXT.encode()).hexdigest(),
                        "source": "test fixture",
                        "slots": [{**SLOT, "quote": TEXT}],
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (root / "prompts/test/transform.yaml").write_text(
        yaml.safe_dump({"version": "test", "styles": {"paraphrase": {"a": "test instruction"}}}),
        encoding="utf-8",
    )
    (root / "prompts/test/read_slots.txt").write_text("test-only reader", encoding="utf-8")
    (root / "predictions/test.md").write_text("test-only prediction", encoding="utf-8")
    config_path = root / "configs" / f"{name}.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment": name,
                "description": "test fixture",
                "language": "sv",
                "generations": generations,
                "corpora": [{"path": "corpus/test_inline.yaml", "styles": "all"}],
                "prompts": "prompts/test/transform.yaml",
                "reader_prompt": "prompts/test/read_slots.txt",
                "prediction": "predictions/test.md",
            }
        ),
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def experiment_root(tmp_path: Path) -> Path:
    """A temporary project root whose default pilot and recursive configs exist."""
    write_experiment(tmp_path, "pilot-sv", generations=1)
    write_experiment(tmp_path, "allegoria-sv", generations=3)
    return tmp_path
