"""The experiment engine: recorded, resumable, paid model calls.

``provider``
    The only module that talks to a model provider. Everything else sees a
    payload going in and raw response bytes coming out.

``plan``
    The frozen design of a run: which passages, which instructions, how deep.

``pilot`` / ``run``
    The bounded one-generation pilot, and the recursive chains. Both write
    append-only receipts, settle a USD budget against actual usage, and never
    build a generation on a fabricated parent.

Nothing here decides what a text *means*. Reading a text is measurement, and it
happens through ``simulacria.measurement`` with a different model.
"""

from __future__ import annotations
