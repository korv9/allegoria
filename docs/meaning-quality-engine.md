# Allegoria as a meaning quality engine

Written after the debate-analysis work. This documents two things the project
now needs kept apart: the **engine** (a small, deterministic, reusable core) and
the **applications** built on or beside it (the LLM-drift research, and the
Riksdagen debate analysis). It also lays out how to grow the engine into a
reusable *meaning quality engine*, and how to produce drift **without an LLM**.

---

## Two tracks, kept honest

The last stretch of work pivoted a long way from the founding question. These
are now two different things and should be labelled as such.

### Track A — the engine (Allegoria proper)
A deterministic, model-free classifier of **signed** change in normative meaning.
Given a source's hand-annotated deontic slots and a reading of a derivative text,
it says per slot whether the change **loosens** (permitted world-states grow) or
**tightens** (they shrink), and reports a non-netted count vector per passage.

- Code: `simulacria/measurement/direction.py` (the classifier + 15 ratified test
  cases) and `simulacria/measurement/changes.py` (the reading→change bridge).
- Properties: pure, deterministic, no network, no model. Domain-agnostic — it
  imports nothing about SFS, RFC or debates.
- This is the actual contribution of the project. Everything else is a producer
  of its inputs or a consumer of its outputs.

### Track B — the applications
| Application | Uses the engine? | What it is |
|---|---|---|
| LAS 6 § fidelity (`corpus/claims_v2_las.yaml`) | ✅ yes | real slot readings through `changes.py` |
| Two proposals (`corpus/claims_v3_proposals.yaml`) | ✅ yes | `classify(whole_part)` |
| Original LLM-drift loop (`generation/`, twinning) | ⏸ intended, not run | the founding research question; zero real runs |
| Per-issue direction screen (`proposal_scan.py`) | ❌ no | lexical keyword screen |
| Vote × direction explorer (`law_positions.py`) | ❌ no | lexical screen + real votes |

**The honest line:** the large interactive Riksdagen tools are *not the engine*.
They borrow its vocabulary (loosening/tightening) and are a useful, broad,
demoable product, but they run a lexical proxy — not the deterministic slot
metric. Only the small, hand-annotated measurements exercise the engine. Keep
that distinction visible wherever results are shown.

---

## What makes it an engine (and what is missing)

An engine is a stable core with a contract, swappable edges, and a conformance
suite. The core already has most of this:

- **Contract:** `passage_changes(slots, before, after) -> [ChangeOutcome]` and
  `direction_vector(...) -> (tightening, loosening, neutral)`. Inputs are slot
  states, not text.
- **Conformance suite:** the 15 `DIRECTION.md` cases in `tests/test_direction.py`.
  Any implementation or refactor must keep these green. That is the spec.
- **The seam that makes it reusable — the reader.** Text never enters the engine;
  *slot states* do. Everything between raw text and slot states is a **reader**,
  and readers are swappable:
  - `HumanReader` — hand annotation (what claims_v2 uses; the honest ground truth).
  - `LexicalReader` — regex/marker screen (what the debate tools use; fast, broad,
    false positives; must never be called measurement without saying so).
  - `LLMReader` — a blinded, tightly-constrained extractor, local or API, gated by
    the verbatim-substring check in `slot_reading.validate_reading`.
  The engine does not care which reader produced the states; reader quality is a
  separate question measured by human agreement (PROTOCOL.md).

**Missing for a clean reusable engine:**
1. A named **reader interface** (`read(text, schema) -> {slot_id: SlotState}`) so
   the three readers above are interchangeable behind one type.
2. **Magnitude on the ladder.** Determinacy is three rungs (specific/vague/absent);
   a numeric change like "6 → 12 months" is a real loosening the engine cannot
   sign because both rungs are `specific`. A `bound` needs an ordered magnitude,
   not just determinacy. This is the one known blind spot in the metric today.
3. **Packaging.** The measurement subpackage has no dependency on the rest of the
   repo and could ship as a standalone library (`meaningquality/`) plus a CLI
   (`meaning-quality diff source.yaml target.yaml`), versioned, with the 15 cases
   as its test contract.

---

## Reframe: a signed meaning-quality metric

Stated generally, the engine answers: **given two structured representations of a
rule (or a source plus a reading of a derivative), which way did the norm move?**
That is a *signed semantic-fidelity* measure, and it is not specific to Swedish
statute. Candidate domains where the same slot schema applies:

- **Terms of service / privacy policies** — did an update loosen (more collection
  permitted) or tighten (more user rights)?
- **Contract redlines** — does an edit expand or restrict an obligation?
- **API / protocol specs** — `MUST → SHOULD` is a modality weakening = loosening.
  (The RFC domain already in the repo is exactly this.)
- **Clinical guidelines, regulatory diffs, localization QA** — same shape.
- **LLM output QA** — does a summary or rewrite preserve the obligations of the
  source? (The founding Allegoria use.)

In each case the engine is unchanged; only the corpus adapter and the reader
change. That is the test of a real engine.

---

## Drift without an LLM

The measurement was always model-free; the LLM only ever did two jobs — **produce
drift** (the transformer) and **read slots** (the extractor). Remove both and the
whole pipeline is LLM-free. Ideas, roughly in order of value:

1. **Real historical versions = real drift, no model.** Laws are amended, RFCs are
   obsoleted, ToS are revised — by institutions, not an LLM. Feed the engine
   successive *real* versions of a provision and measure the signed drift across
   amendments. This reconnects to the founding question ("does meaning drift have
   a sign?") using genuine institutional drift, and it is arguably a stronger,
   more novel result than LLM drift — and completely LLM-free. SFS carries
   `valid_from`/`valid_to`; RFCs carry `obsoletes`/`updated-by` chains.
2. **Deterministic degraders as the transformer.** Replace the LLM transformer
   with a rule-based text degrader and run the recursive loop: extractive
   summarization (keep top-k sentences), clause dropping (remove the least-frequent
   clause each generation), truncation, lexicon synonym substitution. These will
   drop qualifiers and can be run for many generations, reproducibly, with no
   model. It is a controlled study of what naive compression does to deontic
   structure — and a clean way to exercise the engine at scale.
3. **Local embedding paraphrase (no generative model).** Replace each sentence
   with its nearest neighbour from a corpus using a local sentence encoder. Drift
   without a generative LLM or any API. (The debate repo already ships such an
   encoder.)
4. **Lexical/rule readers instead of an LLM extractor.** For domains with explicit
   deontic markers (Swedish `ska`/`får`/`undantag`, RFC `MUST`/`SHOULD`), a
   deterministic reader can supply slot states directly — with the standing caveat
   that a marker screen has known false positives and is not measurement-grade
   until its agreement with a human is reported.

The cleanest LLM-free instrument is **(1) + a human or rule reader**: real
versioned corpora in, deterministic signed drift out. No transformer, no
extractor, no network.

---

## Roadmap to the engine

1. Add the **reader interface** and refactor the three existing readers behind it.
2. Add **magnitude** to `bound`/determinacy so numeric cap changes sign.
3. Ingest one **versioned corpus** (a handful of amended SFS provisions, or a
   small RFC obsoletes chain) and measure real historical drift — the first
   LLM-free drift result.
4. Extract `measurement/` into a standalone `meaningquality` package + CLI, with
   the 15 cases as its conformance suite.
5. Keep Track A (engine + drift) and Track B (the debate product) labelled as
   separate throughout; never present the lexical screen as the metric.
