"""The model registry: which models exist, what they cost, who serves them.

One YAML file (`configs/models.yaml`) is the only place a model id appears. Code
looks models up by registry name (what a config asks for) or by wire id (what a
saved response claims to be), and a run records the full resolved spec so a
result can be read years later without guessing what "the cheap reader" meant.

Prices live here rather than in code because they are facts about the world that
change without any code changing, and a stale price makes the budget guard wrong
in the dangerous direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = "configs/models.yaml"
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ModelSpec:
    """One usable model: what to call, through whom, at what price."""

    name: str  # registry key, what a config names
    provider: str  # module under simulacria/providers/
    model: str  # the wire id sent to the API and echoed back
    input_usd_per_million: float
    output_usd_per_million: float
    max_tokens: int
    structured_output: bool
    verified: str | None
    params: dict = field(default_factory=dict)
    notes: str = ""
    # What the account's dashboard allows, when someone has read it off. None
    # means unknown, not unlimited.
    requests_per_minute: int | None = None

    @property
    def prices(self) -> tuple[float, float]:
        return self.input_usd_per_million, self.output_usd_per_million

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_usd_per_million + output_tokens * self.output_usd_per_million
        ) / 1_000_000

    def record(self) -> dict:
        """What a manifest stores: enough to reconstruct the choice, not the key."""
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "input_usd_per_million": self.input_usd_per_million,
            "output_usd_per_million": self.output_usd_per_million,
            "max_tokens": self.max_tokens,
            "params": dict(self.params),
            "verified": self.verified,
            "requests_per_minute": self.requests_per_minute,
        }


@lru_cache(maxsize=4)
def registry(root: Path = PROJECT_ROOT) -> dict[str, ModelSpec]:
    """Every declared model, keyed by registry name."""
    data = yaml.safe_load((root / REGISTRY_PATH).read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{REGISTRY_PATH}: expected schema_version {SCHEMA_VERSION}")
    specs: dict[str, ModelSpec] = {}
    for name, entry in data["models"].items():
        specs[name] = ModelSpec(
            name=name,
            provider=entry["provider"],
            model=entry["model"],
            input_usd_per_million=float(entry["input_usd_per_million"]),
            output_usd_per_million=float(entry["output_usd_per_million"]),
            max_tokens=int(entry["max_tokens"]),
            structured_output=bool(entry.get("structured_output", False)),
            # YAML turns 2026-09-11 into a date; a manifest has to be JSON.
            verified=str(entry["verified"]) if entry.get("verified") else None,
            params=dict(entry.get("params") or {}),
            notes=(entry.get("notes") or "").strip(),
            requests_per_minute=entry.get("requests_per_minute"),
        )
    wire_ids = [spec.model for spec in specs.values()]
    if len(set(wire_ids)) != len(wire_ids):
        raise ValueError(f"{REGISTRY_PATH}: two entries claim the same wire model id")
    return specs


def defaults(root: Path = PROJECT_ROOT) -> dict[str, str]:
    data = yaml.safe_load((root / REGISTRY_PATH).read_text(encoding="utf-8"))
    return dict(data.get("defaults") or {})


def by_name(name: str, root: Path = PROJECT_ROOT) -> ModelSpec:
    known = registry(root)
    if name not in known:
        raise ValueError(f"unknown model {name!r}; declared in {REGISTRY_PATH}: {sorted(known)}")
    return known[name]


def by_model_id(model_id: str, root: Path = PROJECT_ROOT) -> ModelSpec:
    """The spec a saved response belongs to. Raises for anything undeclared."""
    for spec in registry(root).values():
        if spec.model == model_id:
            return spec
    raise ValueError(f"model {model_id!r} is not declared in {REGISTRY_PATH}")


def known_model_id(model_id: str, root: Path = PROJECT_ROOT) -> bool:
    return any(spec.model == model_id for spec in registry(root).values())


def resolve(config: dict, root: Path = PROJECT_ROOT) -> dict[str, ModelSpec]:
    """The transformer and extractor an experiment config asks for.

    PROTOCOL.md requires the two roles to be different models: a model reading
    its own output is not an instrument, it is the same guess twice.
    """
    asked = dict(defaults(root))
    asked.update(config.get("models") or {})
    for role in ("transformer", "extractor"):
        if role not in asked:
            raise ValueError(f"no {role} model: name one in the config or in {REGISTRY_PATH}")
    transformer, extractor = by_name(asked["transformer"], root), by_name(asked["extractor"], root)
    if transformer.model == extractor.model:
        raise ValueError("transformer and extractor must be different models (PROTOCOL.md)")
    if not extractor.structured_output:
        raise ValueError(f"{extractor.name} cannot be the reader: it has no structured output")
    return {"transformer": transformer, "extractor": extractor}


def unverified(specs: dict[str, ModelSpec]) -> list[ModelSpec]:
    """Models in this run that nobody has actually called yet, in role order."""
    return [spec for spec in specs.values() if not spec.verified]


def sampling(specs: dict[str, ModelSpec]) -> dict:
    """What a manifest records about how each model was asked, per role."""
    return {
        role: {
            "model": spec.model,
            "params_sent": dict(spec.params),
            "max_tokens": spec.max_tokens,
            "note": spec.notes,
        }
        for role, spec in specs.items()
    }


def suggested_interval(specs: dict[str, ModelSpec], workers: int = 4) -> float | None:
    """Seconds between call starts the declared rate limits allow, or None.

    Returns None when any model in the run has no recorded limit: a pace derived
    from a guess is worse than the conservative default, because the failure it
    causes is a wall of 429s in the middle of a paid run.
    """
    limits = [spec.requests_per_minute for spec in specs.values()]
    if not limits or any(limit is None for limit in limits):
        return None
    # Half the allowance, so a burst from `workers` threads still fits.
    return round(60 / (min(limits) / 2), 3)
