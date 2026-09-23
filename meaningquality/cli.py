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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "selftest":
        return selftest()
    if argv[0] == "drift" and len(argv) > 1:
        return drift(argv[1])
    print("usage: meaning-quality [selftest | drift <versions.yaml>]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
