"""Command line for the engine.

    python -m meaningquality selftest          run the conformance suite
    python -m meaningquality drift <file.yaml>  sign a version chain (needs pyyaml)

`selftest` proves the engine classifies as the specification says, with no data,
no model and no network -- the quickest way to see it works. `drift` signs each
consecutive version of a rule in a `versions`-style YAML (a `bound` slot with a
numeric `magnitude` per version).
"""

from __future__ import annotations

import sys


def selftest() -> int:
    from meaningquality.conformance import run

    passed, total, failures = run()
    for desc, expected, got in failures:
        print(f"FAIL: {desc} -- expected {expected}, got {got}")
    print(f"{passed}/{total} conformance cases passed")
    return 0 if passed == total else 1


def drift(path: str) -> int:
    import yaml

    from meaningquality.direction import SlotChange, classify

    doc = yaml.safe_load(open(path, encoding="utf-8"))
    for provision in doc.get("provisions", []):
        print(provision.get("title", provision.get("provision_id", "?")))
        versions = provision["versions"]
        unit = provision.get("unit", "")
        for before, after in zip(versions, versions[1:]):
            change = SlotChange.ceiling_bound(before["magnitude"], after["magnitude"])
            print(
                f"  {classify(change).value:<11} {before['magnitude']} -> {after['magnitude']} {unit}"
            )
    return 0


def rfc_inventory(path: str) -> int:
    from meaningquality.rfc import requirements

    reqs = requirements(open(path, encoding="utf-8").read())
    from collections import Counter

    by_mod = Counter(r.modality.name.lower() for r in reqs)
    print(f"{len(reqs)} requirements  {dict(by_mod)}")
    for r in reqs[:10]:
        print(f"  {r.keyword:<10} {r.sentence[:90]}")
    return 0


def rfc_drift(old_path: str, new_path: str) -> int:
    from meaningquality.rfc import drift, requirements

    old = requirements(open(old_path, encoding="utf-8").read())
    new = requirements(open(new_path, encoding="utf-8").read())
    for c in drift(old, new):
        print(
            f"  {c['direction']:<11} {c['from_keyword']} -> {c['to_keyword']}: {c['requirement'][:80]}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "selftest":
        return selftest()
    if argv[0] == "drift" and len(argv) > 1:
        return drift(argv[1])
    if argv[0] == "rfc" and len(argv) > 1:
        return rfc_inventory(argv[1])
    if argv[0] == "rfc-drift" and len(argv) > 2:
        return rfc_drift(argv[1], argv[2])
    print(
        "usage: meaning-quality [selftest | drift <versions.yaml> | rfc <rfc.txt> | rfc-drift <old> <new>]"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
