"""Re-export shim. The reading-to-change bridge now lives in the standalone
`meaningquality` package; edit it there. This keeps existing imports
(`simulacria.measurement.changes`) working unchanged."""

from __future__ import annotations

from meaningquality.changes import (
    ChangeOutcome,
    passage_changes,
    passage_vector,
    read_change,
    unobservable_reasons,
)

__all__ = [
    "ChangeOutcome",
    "passage_changes",
    "passage_vector",
    "read_change",
    "unobservable_reasons",
]
