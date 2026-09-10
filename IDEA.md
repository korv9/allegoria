# Allegoria / Simulacria

**Meaning has a direction when it breaks down. Almost nobody measures the sign.**

This document explains the idea behind the project — not how it is built, but
why it exists and what it claims. Implementation decisions live in
`DATA_DECISIONS.md`.

---

## How it started

Allegoria began as a joke on Legora: a RAG system over Swedish statutory law
where every answer was converted into an allegory. A pure spinoff. Ask "what
applies on termination of employment?" and you got a parable instead of a
provision.

Something became obvious during the build that had not been the point. When a
legal text becomes an allegory, it is not only the style that goes — *the
meaning shifts*. And it does not shift at random. Some things survive, others
fall, and they fall in a particular order.

That is where the joke turned into a research project. Simulacria is the name of
the question: **what happens to meaning when text passes through repeated LLM
transformations?**

---

## The core observation

An early run on a fictional passage about rest periods produced a result nobody
had predicted.

The passage contained a rule, an exception to the rule, and a qualifier on the
exception — roughly: *"Rest shall be granted. An exception may be made in the
event of an unforeseen occurrence, provided that compensation is given within
seven days."*

The naive assumption is that degradation is subtractive: detail falls away, the
text gets thinner, and eventually only the main rule is left. That is not what
happened.

**The qualifier died before the exception did.**

After a few generations what remained was *"Rest shall be granted. An exception
may be made in the event of an unforeseen occurrence."* The compensation
requirement was gone. The exception was still there.

The effect is that a permission **broadened**. The text did not become poorer in
permission — it became richer. A conditional exception had become
unconditional. Measured as information loss this looks like mild degradation.
Measured as legal effect, it is a different rule.

That is the project's starting point.

---

## What actually gets measured: `direction`

If degradation can run two ways, the metric needs a sign.

`direction` classifies each generation relative to its parent into one of three
states:

| State | Meaning |
|---|---|
| `tightening` | Normative force is narrowed — conditions added, permission constrained |
| `loosening` | Normative force is relaxed — conditions dropped, permission widened |
| `neutral` | No directional change in deontic structure |

The computation is **deterministic**, not delegated to a judge model. It rests
on slots defined in the corpus: which actors, deadlines, conditions and
modalities are supposed to be present. A slot is either preserved, removed or
altered, and the direction follows from what kind of slot it is. A dropped
condition on an exception is `loosening`. An added condition on a main rule is
`tightening`.

The same principle governs `origin_type` (`SOURCE` / `DERIVED` / `EMERGENT`),
which is derived from source entailment support and DAG parentage rather than
from a model's judgment. The reason is identical in both cases: if the
instrument is an LLM, you are measuring two systems at once and cannot separate
them.

---

## Why not just cosine similarity

The obvious move is to embed each generation and measure its distance from the
source. It yields a clean, monotonically falling curve that looks scientific.

It cannot see what this project is about.

*"An exception may be made in the event of an unforeseen occurrence, provided
that compensation is given"* and *"An exception may be made in the event of an
unforeseen occurrence"* sit extremely close together in vector space. Nearly all
the words are the same, the syntax is the same, the subject matter is the same.
An embedding reports high similarity. The difference in legal effect is total.

Embeddings are therefore used as a **secondary, descriptive** metric — useful
for plotting drift and for surfacing anomalies worth inspecting by hand. They
are not the source of truth.

---

## Corpus twinning

One problem with running degradation over real statutory text is that the model
may have seen it. If a formulation survives ten generations, you cannot tell
whether the transformation preserved it or the model simply knew it by heart.

The fix is pairwise construction. Every passage exists in two versions:

- **Authentic** — real SFS text
- **Fictional twin** — identical syntactic structure, different actors,
  different numbers, different subject domain

Same sentence architecture, same slot count, same deontic pattern. The only
difference is that the fictional one never existed.

The retention gap between the twins **is** the memorization effect. No
annotation required, no estimation. It is the control group.

---

## Transformation severity as an axis

Allegorization is not a product sitting on top of the engine. It is a *mode*
inside it — and happens to be the most extreme one.

Where the literature mostly runs paraphrase and translation chains (small hops,
many iterations), an allegorization swaps out the entire reference domain in one
step. Legal subjects become figures, deadlines become seasons, sanctions become
fates. Actors and numbers are destroyed by construction.

This makes allegory a sharper instrument, not a blunter one. The only thing that
*can* survive an allegorization is the deontic structure — must, may, may not,
the exception, the qualifier. Allegory isolates what is being measured by
obliterating everything else.

Hence a dose-response axis, using the same loop and the same corpus:

```
paraphrase  →  summarize  →  explain-to-a-layperson  →  allegorize
```

If qualifier death occurs at generation 8 under paraphrase and generation 2
under allegory, the finding stops being an anecdote and becomes a curve.
`transform_style` is therefore a first-class dimension in the run manifest,
alongside prompt version and model string.

---

## Relation to existing work

That iterative LLM generation distorts information is not undiscovered ground.
There is established work here — among others *LLM as a Broken Telephone*
(Mohamed et al., ACL 2025), which ran translation chains through the same model
a hundred times and documented progressive factual distortion, and comparable
studies of drift in unified vision-language models under repeated
self-composition.

What that literature lacks is the sign.

The reported measures are uniformly reference similarity — BLEU, chrF, ROUGE,
METEOR, BERTScore, cosine. All of them unsigned. They can say that meaning
moved; they cannot say which way.

Strikingly, the direction is often *observed* anyway without being measured.
Work on agent memory describes the same pattern in another domain: a mild
preference is progressively rewritten into a strong one until it violates what
the user actually said — and then formalizes drift as one minus cosine
similarity, i.e. back to a scalar that cannot distinguish intensification from
attenuation.

The contribution here is not "meaning degrades recursively". It is:

1. that the degradation has a **sign**
2. that the sign is what matters normatively
3. that it can be measured **deterministically** against constructed ground truth
4. that **corpus twinning** separates memorization from preservation without
   annotation

Swedish statutory text is a suitable substrate because deontic modality is
explicit and the slot structure can be constructed without interpretive
disputes.

---

## What this project is not

**Not RAG.** It was in the original idea but does not belong to the research
question. The loop retrieves nothing — generation N+1 takes generation N
directly. The parent is known.

**Not model collapse.** That literature concerns *training* models on synthetic
data. Everything here happens at inference; the weights are never touched.

**Not an LLM judge.** Both `direction` and `origin_type` are derived, not
adjudicated. An instrument built from the same kind of system it measures is not
an instrument.

**Not a product.** The Allegoria surface is presentation. The claim stands or
falls on the measurement.

---

## The names

**Simulacria** is the engine and the method — the recursive transformation loop,
the measurement, the lineage DAG. It is the name used when the method is written
up.

**Allegoria** is the origin, the most extreme transformation mode, and the name
that works when someone asks what this is. The joke lands immediately and
explains itself.

The split is rhetorical, not architectural. One repo, one engine, one loop.

---

## Deliverables in priority order

1. **`direction`** — slot schema and deterministic computation. This *is* the
   contribution; everything else is scaffolding around it.
2. **The loop + the twinned corpus** — the minimum machinery that produces
   direction data.
3. **Metrics across generations** — turns the finding into a curve.
4. **The Meaning Lineage graph** — a DAG over meanings at proposition level,
   with `origin_type` per node. Presents 1–3.
5. **The Allegoria surface** — last, if at all.

The graph deliberately sits below the measurement. A visualization built before
the thing it visualizes tends to shape the measurement toward whatever looks
good.
