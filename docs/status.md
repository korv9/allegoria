# Status: what the codebase does, and what comes next

Written 2026-09-12, after the restructure into layers and domains. Counts come
from `notebooks/00_data_overview.ipynb`, which recounts them from disk on every
run. Read that notebook rather than trusting the numbers here if they disagree.

## What works today

**Selection — finding provisions worth looking at.** 50 Swedish laws parse into
1,952 provisions (a contract the build refuses to violate), scored by 28 duty /
exception / qualifier markers into 461 ranked candidates with 8,983 marker hits.
A larger v2 pool holds 18,836 provisions from 466 documents. These are lexical
aids with known false positives, not measurements.

**Datasets are pluggable.** Three domain adapters: `sfs` (Swedish statute,
verified back to the original XML bytes), `rfc` (English IETF plain text, cut by
numbered section), `inline` (text carried in the corpus, pinned by hash). Three
annotated corpora: 3 statutory passages / 15 slots, 30 philosophical controls /
90 slots, 3 RFC sections / 12 slots. All slot annotations are assistant drafts
with no human review.

**Experiments are configuration.** `configs/pilot-sv.yaml` (24 transformations,
1 generation), `configs/allegoria-sv.yaml` (84 chains, 10 generations, 840
transformations and 873 readings), `configs/rfc-en.yaml` (24 chains, 240
transformations). `--check` plans and validates any of them without spending.

**Model choice is configuration.** `configs/models.yaml` declares six models with
prices and verification dates; an experiment names two of them, and
`--transformer` / `--extractor` override them for a one-off. Two providers are
implemented: Anthropic (verified) and OpenAI (fixtures only, unverified).

**The run engine.** By default `sonnet-5` transforms and `haiku-4-5` reads. Every paid attempt writes a receipt with the
raw bytes and their hash; a budget reservation is settled against actual billed
usage; a refusal or truncation ends its own chain and is recorded rather than
retried; a bad reading is retried once and then flagged; a run resumes from its
receipts without repeating work.

**Verification and analysis.** `load_run` replays every saved row against the
raw responses and refuses a run whose evidence does not match. A DuckDB
projection holds runs, texts, source slots, readings, slot observations and call
events, plus a `slot_comparisons` view that lines up source, parent and child.
81 tests pass and one frozen determinacy fixture fails by design
(`sfs-2026-1283:K5P1`), which is left red on purpose.

**Notebooks.** Data overview (00), pipeline walkthrough (01), normative axis with
real lexical results (02), generation-one reader (03), recursive results (04),
Parquet browser (05). None of them simulate a missing result.

**Exploratory analysis.** `eda/` holds five notebooks that use no model at all:
the corpus landscape, how the markers behave including their failure modes,
whether the shortlist is really a length ranking, the annotated slots across the
three domains, and which analyses the data can and cannot carry.

## What does not exist yet

- **No Anthropic run has been made.** Zero rows in every research table. The one
  partial run on disk is from the retired OpenAI configuration; it is preserved
  byte-identical, refused by `load_run`, and cannot be resumed.
- **The direction metric is wired but starved of data.**
  `simulacria/measurement/direction.py` implements the ratified derivation rule
  (DD051/DD052) deterministically, `tests/test_direction.py` pins all fifteen
  `DIRECTION.md` table entries (cases 1--14 plus 9b), and
  `simulacria/measurement/changes.py` bridges a blinded reading to a `SlotChange`.
  The statutory corpus (`law_probe_v1.yaml`) now carries draft determinacy and
  modality rungs. Two real limits remain. First, no run exists, so there is
  nothing to classify. Second, the bridge is only as sharp as the reader: a
  present/absent reading resolves a slot vanishing (an exception removed, a
  qualifier dropped to `absent`) but not a `specific -> vague` step, so those are
  reported as unobservable rather than counted as neutral. Seeing the middle rung
  needs either a determinacy question in the reading or a stronger reader.
- **No human review of any slot.** Every annotation is an assistant draft, and
  no inter-annotator agreement figure exists.
- **The reader is weak.** A nine-reading live check found 3 invalid quotes and no
  detection of the one shift Opus 5 had caught. See
  `predictions/2026-09-11-amendment-cheapest-models.md`.
- **Databricks is unverified.** `products/allegoria/` has never run in Unity
  Catalog, and `DD041` records a latent Bronze/Silver column mismatch.

## Next steps, in the order they unblock each other

1. **Decide the reader.** The cheapest pair costs about USD 7 for a full Swedish
   run but has not shown it can see a normative shift; Opus 5 costs about USD 17
   and has. Cheapest honest option: `--group statutory --extractor opus-5`, for
   roughly USD 5. This is now a one-word config change, so it is purely a
   spending decision -- see `docs/models.md`.
2. **Run the statutory group and read the actual texts.** Nothing downstream is
   worth building before there is one verified run to look at.
3. **Human-review the 15 statutory slots** against the source text, and record
   disagreement. This is what turns readings from observations into evidence.
4. **Human-review the direction annotations and sharpen the reader.** The
   classifier (`direction.py`), the reading bridge (`changes.py`) and draft
   determinacy/modality rungs on the statutory corpus now exist. What remains is a
   person confirming those draft rungs, and deciding how the middle of the ladder
   (`specific -> vague`) gets seen -- a determinacy question in the reading, or a
   stronger reader -- since a binary reader leaves it unobservable. Then extend
   the slot contract to `ceiling`/`bound`, which `DIRECTION.md` ratified but the
   corpus vocabulary (`SLOT_KINDS`, `ATTACHMENTS`) does not yet carry. Report
   remaining encoding ambiguities; prepare the requested review packet without
   confirming its drafts.
5. **Then the RFC domain**, as a check that the effect is not about Swedish. Not
   a replication, and never pooled with the Swedish results.
6. **Optional, once a run exists:** batch the readings for a 50% discount, and
   lower the 6.2-second inter-call interval inherited from the OpenAI rate limit.

## Open questions that need a person, not code

- Is `dock` a carve-out or a ceiling? Removing one loosens, the other tightens.
  (`review/2026-09-11/DIRECTION-ceiling-proposal.md`)
- Should the `om inte` wildcard fix ship at a 45.8-point recall cost?
  (`review/2026-09-11/REVIEW.md`)
- What counts as sufficient human agreement before any number is published?
