# Design note: the RFC domain

A pre-run design note for `configs/rfc-en.yaml`, written 2026-09-12. Like every
file in this folder it is **not** a committed or externally timestamped
preregistration, and it does not amend the Swedish experiment.

## Why a second domain exists

The claim under test -- that recursive rewriting loosens normative structure,
and that conditions on an exception go before the exception itself -- is not a
claim about Swedish. If it only ever holds on three statutory provisions in one
language, the finding is about that corpus.

English RFCs are the cheapest honest second case. Their normative vocabulary is
explicit and conventionalised (MUST, MUST NOT, SHOULD, MAY), departures are
written out ("there may exist valid reasons in particular circumstances to
ignore a particular item"), and the conditions on those departures are stated in
the same sentence. Duty, exception and condition therefore mean the same here as
in statute, which is what makes the two corpora comparable at all.

## What is fixed before any run

- Corpus: `corpus/rfc_probe_v1.yaml` -- three sections, twelve slots.
  `rfc-2119:3`, `rfc-2119:6`, `rfc-6265:4.1.2.5`.
- Source bytes: `data/source/rfc/`, pinned by SHA-256 in `data/bronze/rfc/`.
  Sections are cut from the plain text by numbered heading; page headers and
  footers are dropped, and the heading line stays with its section.
- Prompts: `prompts/en/transform.yaml`, a line-by-line mirror of the Swedish
  instructions, and `prompts/en/read_slots.txt` for the reader.
- Instrument: unchanged. Same slot vocabulary, same blinding, same reading
  schema, same receipts, same budget. A domain may change the text; it may not
  change the instrument.

## What this domain does not do

- It is not a replication and its results are not pooled with `allegoria-sv`.
  Two corpora, two languages and two registers differ in more ways than one.
- The twelve slots are assistant drafts with no human review, exactly as in the
  Swedish corpus, and the same reservation applies to any number computed from
  them.
- `rfc-2119:3` and `rfc-2119:6` are text *about* normative language. That makes
  them convenient and also unusual: a model rewriting them is rewriting a
  definition of duty, not a duty. `rfc-6265:4.1.2.5` is included because it is
  an ordinary protocol requirement.
- No run has been made in this domain. Nothing here reports a result.
