# PROTOCOL.md

How the measurement is kept honest. `DIRECTION.md` defines *what* is measured;
this file covers *how* it is read off without the result being smuggled in.

Read both before implementing anything in the extraction or run pipeline.

---

## Three roles, kept separate

| Role | Implemented by | May it be biased? |
|---|---|---|
| **Transformer** | An LLM | Yes — it is the object of study |
| **Classifier** | Deterministic code | No, and it is not |
| **Extractor** | LLM, tightly constrained | **This is the weak point** |

`direction` is computed from slot states via the derivation rule in
`DIRECTION.md`. No model judges it. But something has to determine that
generation 4's text has `deadline = absent`, and that reading is not given.

If the extractor is sloppy, a judge model has re-entered the design one step
earlier than where anyone was looking. Everything below exists to prevent that.

---

## Extraction rules

### Ask mechanical questions, never the hypothesis

Never ask "has the meaning loosened?" — that requests the answer you hope for.
Ask per slot, in a form close to transcription:

```
Finns det en tidsfrist i den här texten? Citera den ordagrant.
Om ingen finns, svara NONE.
```

The classifier then computes direction from the answers.

**The words "loosening", "tightening", "degradation", "drift" and "qualifier
death" must never appear in any prompt used for measurement.** Grep for them in
the prompt directory as a CI check.

### Require verbatim quotation

The extractor returns the exact span, not a paraphrase. A quote can be verified
against the source text programmatically; a paraphrase cannot. If the returned
span is not a substring of the input, the extraction failed — retry, then flag
for manual review. Do not silently accept it.

### Blinding

The extractor sees the generation text and the slot schema. It must **not** see:

- the source passage
- the generation number
- the `transform_style`
- whether the passage is authentic or a fictional twin
- any earlier generation

Pool all generations from all runs, shuffle, then extract. Without shuffling the
extractor drifts toward "finding" degradation at high generation numbers because
it knows they are high.

### Separate models

The model that transforms must never be the model that extracts. A model
assessing its own output is not an instrument. Record both model strings in the
manifest.

---

## Human agreement check

Hand-annotate at least 20% of extractions, blinded the same way, and report
agreement between human and extractor.

This number belongs in the write-up whether it is flattering or not. If
agreement is low, the metric is not trustworthy — and knowing that is worth more
than not knowing it. Do not tune the extractor prompt against the full set until
agreement is measured; that turns the check into a fitting exercise.

Report per slot kind. Agreement on `deadline` will likely be higher than on
`condition`, and that difference is informative.

---

## The transformation prompt is a variable

Restrictive prompting preserves text substantially better than loose prompting —
this is established in the iterative-generation literature. Your prompt
therefore partly determines your result.

Two failure modes:

- **"Preserve all conditions exactly"** — suppresses the effect under study
- **"Make this simpler and easier to read"** — *orders* loosening

The transformation prompt must be neutral with respect to deontic structure. It
instructs on form, not on what should survive.

### Required variation

- **At least two prompt variants per run.** If the finding appears under only
  one, it is a prompt artifact, not a property of transformation.
- **At least two transformer models.** Rules out single-model idiosyncrasy.
- Prompts are versioned files, never inlined. `prompt_version` goes in the
  manifest.

---

## Preregistration

Before the first real run, commit predictions to the repo so they carry a git
timestamp.

There is already a hypothesis — qualifiers die before exceptions. That makes the
design biased in a way no amount of care removes. Preregistration is not a
formality here; it is the difference between "I predicted this" and "I tuned a
metric until it showed what I had already seen".

Use `predictions/YYYY-MM-DD-<name>.md`:

```markdown
# Prediction: <name>
Date: <committed before the run>
Corpus version: <hash>

## Predicted direction by slot kind
- condition on exception: loosening, first observed around generation N
- deadline: weakened before absent, ladder step visible around generation N
- modality: ...

## Predicted ordering
Qualifiers reach `absent` before exceptions are removed.

## What would falsify this
- Qualifiers and exceptions degrade at indistinguishable rates
- Direction is dominated by tightening rather than loosening
- The authentic/fictional retention gap is large enough that the
  effect is memorization, not transformation

## Accepted null result
If qualifiers and exceptions degrade at the same rate, that is an answer.
It gets written up.
```

Amendments are allowed. They are added as new commits with reasons, never by
editing the original file.

---

## Run integrity

- **Freeze the corpus before the run.** Record its hash. A corpus edited
  mid-experiment invalidates the run
- **Pin the exact model version string.** Aliases move
- **Retain raw responses.** Every API response is stored unparsed alongside the
  parsed record. Parsing bugs are recoverable; discarded responses are not
- **Record failures.** Refusals, truncations, timeouts and malformed output are
  data. Silently dropping them biases the sample toward passages the model found
  easy
- **Never re-run and overwrite.** A new run gets a new `run_id`

---

## Analysis discipline

- **Fix the analysis before looking at results.** Which comparisons, which
  stratifications, in what order — decided in advance
- **Do not select passages after the fact.** Reporting the subset where the
  effect is clearest is the most common way an honest project becomes a
  dishonest one
- **Report `loosening_count` and `tightening_count` separately.** Never a net.
  See `DIRECTION.md`
- **Report the twin gap even when it is inconvenient.** If fictional twins
  degrade much faster than authentic ones, the effect is substantially
  memorization, and that is the finding

---

## Checks worth automating

- No banned vocabulary in measurement prompts
- Every extracted span is a verbatim substring of its input
- Manifest completeness — refuse to start a run with a missing field
- Corpus hash matches the one recorded at run start
- Test case 9 from `DIRECTION.md` still returns `(1, 1, 0)`

---

## Status

Proposed in session, **not yet ratified in `DATA_DECISIONS.md`**. Implement
against it; escalate to Anton rather than improvising if something here proves
unworkable in practice.
