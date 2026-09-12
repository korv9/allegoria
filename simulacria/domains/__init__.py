"""What counts as a dataset: one adapter per corpus, behind one small contract.

The experiment is about what recursive rewriting does to normative text. Which
normative text is a parameter, not a premise. A domain adapter answers three
questions for its own corpus and nothing else:

- how a passage id resolves to text (``resolve``),
- how that text's lineage is verified back to original bytes,
- which slot kinds and attachments its annotations may use.

Everything downstream -- the budget, the receipts, the chains, the slot reading,
the DuckDB projection -- is domain-agnostic and must stay that way. Adding a
corpus means adding an adapter here and a corpus YAML that names it; it must
never mean editing ``simulacria.generation`` or ``simulacria.measurement``.

See ``docs/new-domain.md`` for the checklist.
"""

from __future__ import annotations

from simulacria.domains.base import Domain, PassageSource, get, names, register

__all__ = ["Domain", "PassageSource", "get", "names", "register"]
