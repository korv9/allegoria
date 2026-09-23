"""The deterministic RFC 2119 reader and the modality drift it feeds the engine."""

from pathlib import Path

from meaningquality.direction import Modality
from meaningquality.rfc import Requirement, drift, profile, requirements

ROOT = Path(__file__).resolve().parents[1]

SNIPPET = """
   Servers SHOULD limit the number of cookies.

   User agents MUST implement the more liberal processing rules.

   The key words "MUST", "SHOULD" and "MAY" in this document are to be
   interpreted as described in RFC 2119.

   Origin servers MAY send a Set-Cookie header.
"""


def test_reader_classifies_and_skips_boilerplate():
    reqs = requirements(SNIPPET)
    kinds = {(r.keyword, r.modality) for r in reqs}
    assert ("SHOULD", Modality.WEAK) in kinds
    assert ("MUST", Modality.BINDING) in kinds
    assert ("MAY", Modality.ABSENT) in kinds
    # the RFC 2119 notation sentence quotes the keywords; it is not a requirement
    assert all("interpreted as described" not in r.sentence for r in reqs)


def test_drift_signs_a_downgrade_and_upgrade():
    must = [Requirement("Servers MUST limit the number of cookies.", "MUST", Modality.BINDING)]
    should = [Requirement("Servers SHOULD limit the number of cookies.", "SHOULD", Modality.WEAK)]
    # MUST -> SHOULD relaxes the obligation: loosening.
    down = drift(must, should)
    assert len(down) == 1 and down[0]["direction"] == "loosening"
    # SHOULD -> MUST hardens it: tightening.
    up = drift(should, must)
    assert len(up) == 1 and up[0]["direction"] == "tightening"
    # unchanged keyword -> no signed change
    assert drift(must, must) == []


def test_profile_shares_sum_and_count():
    reqs = [
        Requirement("a MUST b", "MUST", Modality.BINDING),
        Requirement("c SHOULD d", "SHOULD", Modality.WEAK),
        Requirement("e MAY f", "MAY", Modality.ABSENT),
        Requirement("g MUST h", "MUST", Modality.BINDING),
    ]
    p = profile(reqs)
    assert p["requirements"] == 4
    assert p["counts"] == {"binding": 2, "weak": 1, "absent": 1}
    assert p["shares_pct"]["binding"] == 50.0


def test_reads_the_real_committed_rfc_6265():
    path = ROOT / "data/source/rfc/rfc-6265.txt"
    if not path.exists():
        return
    reqs = requirements(path.read_text(encoding="utf-8"))
    assert len(reqs) > 30
    assert any(r.modality is Modality.BINDING for r in reqs)
    assert any(r.modality is Modality.WEAK for r in reqs)
