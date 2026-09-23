# meaningquality

A signed, deterministic **meaning-quality** metric. Given a source rule and a
reading of a derivative — a rewrite, a description, or a later version — it says
per slot whether the norm **loosened** (the set of permitted actions grows) or
**tightened** (it shrinks), reported as a non-netted count vector.

Most "meaning drift" work reports *unsigned* similarity (BLEU, cosine): it can
say meaning moved, not which way. This engine gives the **sign**, and it does so
**deterministically** — no model, no network, standard library only. It is the
core extracted from the Allegoria / Simulacria project so it can be reused on its
own; the specification is `DIRECTION.md` in the parent repo.

## Why it is an engine

Text never enters the engine — **slot observations** do. Everything between raw
text and observations is a *reader*, and readers are swappable (human annotation,
a lexical marker screen, an LLM extractor). That seam is what makes the same core
work on Swedish statute, an RFC's `MUST`/`SHOULD`, a contract redline or a
privacy-policy change. The 15 ratified cases in `conformance.py` are the contract
any build must keep.

## Use

```python
from meaningquality import measure, SlotChange, Part, Presence, classify

# classify one change
classify(SlotChange.whole_part(Part.EXCEPTION, Presence.REMOVED)).value   # "tightening"
classify(SlotChange.ceiling_bound(6, 12)).value                          # "loosening"

# compare a reading of a derivative to the source, over the source's slots
source = [{"slot_id": "cap", "kind": "bound", "attaches_to": "ceiling", "determinacy": "specific"}]
before = {"cap": {"status": "present", "determinacy": "specific"}}
after  = {"cap": {"status": "present", "determinacy": "vague"}}   # softened
measure(source, before, after)["vector"]                          # (0, 1, 0) -> a loosening
```

## Command line

```
python -m meaningquality selftest            # run the conformance suite (no data needed)
python -m meaningquality drift versions.yaml  # sign a version chain (needs pyyaml)
```

## Reusing it standalone

The package is pure standard library (the CLI's `drift` command needs `pyyaml`).
It has no dependency on the rest of the repository, so it can be vendored by
copying the `meaningquality/` directory, or installed from the repo
(`pip install -e .` exposes the `meaning-quality` command). Run `selftest` after
any move to confirm the engine still classifies as specified.
