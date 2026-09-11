"""Selection heuristics: which provisions are worth a human's attention.

Marker sets, the determinacy ladder, pool loading, scoring and ranking. Every
module here is recall-tuned and carries known false positives. Nothing here is
authoritative about what a provision means, and nothing here may be imported by
`simulacria.measurement` -- see the package docstring in `simulacria/__init__`.
"""

from __future__ import annotations
