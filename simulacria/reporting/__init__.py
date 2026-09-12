"""Reading recorded runs back: verification, views and portable exports.

``runs``
    Loads a run directory and replay-verifies it against its raw responses
    before anything is reported from it. A run that fails verification raises
    rather than reporting a partial number.

``view``
    Tables, curves and HTML cards for notebooks. Gaps stay gaps: a missing
    reading is never filled in or interpolated.

``export``
    Portable copies for review: Parquet, JSON and a blinded review packet.

Nothing here writes into a run directory. Reporting is read-only over evidence.
"""

from __future__ import annotations
