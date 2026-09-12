"""The frozen design of a run, built from an experiment config rather than code.

An experiment names its corpora, its prompts and its depth in one YAML file
under `configs/`. Nothing about Swedish statute is written into this module, so
running the same experiment on RFCs, policy documents or contracts is a new
config plus a corpus -- never an edit here.

What a config may not change is the instrument: slot vocabulary, blinding, the
reading schema and the receipts are the same for every dataset, because results
from two corpora are only comparable while the instrument is identical.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import yaml

from simulacria.generation.models import resolve as resolve_models
from simulacria.measurement.corpus import load_corpus

DEFAULT_CONFIG = "configs/allegoria-sv.yaml"
PILOT_CONFIG = "configs/pilot-sv.yaml"


def load_config(root: Path, path: Path | str = DEFAULT_CONFIG) -> dict:
    """Read and check an experiment config. Every path in it must exist now."""
    config_path = root / path if not Path(path).is_absolute() else Path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for field in ("experiment", "corpora", "prompts", "reader_prompt", "generations"):
        if field not in config:
            raise ValueError(f"{config_path.name}: config is missing {field!r}")
    if not 1 <= config["generations"] <= 10:
        raise ValueError(f"{config_path.name}: generations must be between 1 and 10")
    for relative in [c["path"] for c in config["corpora"]] + [
        config["prompts"],
        config["reader_prompt"],
    ]:
        if not (root / relative).is_file():
            raise ValueError(f"{config_path.name}: {relative} does not exist")
    # Resolving here means a config naming an unknown model, or the same model
    # for both roles, fails before a run directory is created rather than after.
    resolve_models(config)
    config["config_path"] = str(Path(path).as_posix())
    return config


def reader_instruction(root: Path, config: dict) -> str:
    return (root / config["reader_prompt"]).read_text(encoding="utf-8")


def plan(root: Path, config: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Passages and the chains to run over them, in a stable order.

    A chain is one passage under one instruction, followed for as many
    generations as the config asks for. Variants a and b are different
    instructions, not repetitions of the same treatment.
    """
    config = config or load_config(root)
    prompts = yaml.safe_load((root / config["prompts"]).read_text(encoding="utf-8"))
    sources: list[dict] = []
    chains: list[dict] = []
    for entry in config["corpora"]:
        passages = load_corpus(root / entry["path"], root)
        wanted = entry.get("styles", "all")
        styles = prompts["styles"] if wanted == "all" else {s: prompts["styles"][s] for s in wanted}
        for passage in passages:
            sources.append(passage)
            for style, variants in styles.items():
                for variant, instruction in variants.items():
                    chains.append(
                        {
                            "chain_id": f"{passage['passage_id']}:{style}:{variant}",
                            "passage_id": passage["passage_id"],
                            "style": style,
                            "variant": variant,
                            "instruction": instruction,
                        }
                    )
    if len({s["passage_id"] for s in sources}) != len(sources):
        raise ValueError("passage ids collide across the configured corpora")
    return sources, chains


def digest(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
