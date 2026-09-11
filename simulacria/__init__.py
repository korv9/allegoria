"""Simulacria -- the research core.

The package is split along the line the project exists to defend:

``simulacria.selection``
    Heuristics that decide which provisions are *worth looking at*. Marker
    regexes, the determinacy ladder, scoring and ranking. Recall-tuned, full of
    false positives, and never authoritative about meaning.

``simulacria.measurement``
    The metric itself -- ``direction``, the slot schema, the contracts. Computed
    deterministically from hand-annotated slot state, per ``DIRECTION.md``.

**Measurement must never import from selection.** The reason qualifier
attachment is hand-annotated rather than inferred is that it decides the sign;
letting a selection heuristic supply it would put a guess inside the instrument.
``PROTOCOL.md`` makes the same argument about LLM judges: an instrument built
from the thing it measures is not an instrument. A flat package would make that
leak a one-line import that nobody notices in review. Here it is a new
dependency edge between two named subpackages, visible in any diff.

Selection may not import from measurement either, but for a duller reason: it
has no need to, and the day it does, the heuristic has started chasing the
metric.
"""

from __future__ import annotations

__all__ = ["selection"]
