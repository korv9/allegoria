# Simulacra: the philosophy behind the measurement

Why the project is named *Simulacria* and *Allegoria*, what it borrows from
Baudrillard, and how that connects to deontic logic and the semantics of drift.
This is the conceptual frame; the metric is specified in `DIRECTION.md` and built
in `meaningquality/`.

---

## The map and the territory

Baudrillard opens *Simulacra and Simulation* by inverting Borges' fable of a map
so detailed it covers the empire exactly. In the fable the map decays and the
territory endures. Baudrillard says the modern condition is the reverse: **the
map precedes the territory** — the model, the copy, the representation comes
first, and the real is generated from it. When the sign no longer refers to any
original, it is a *simulacrum*, and a world made of such signs is *hyperreal*.

He sketches four successive orders of the image:

1. it is a faithful **reflection** of a reality;
2. it **masks and distorts** a reality;
3. it **masks the absence** of a reality;
4. it is a **pure simulacrum** — it bears no relation to any reality; it is its
   own pure simulation.

A norm and its restatements sit exactly on this ladder. A statute is the
territory. A faithful summary is order 1. A description that quietly widens a
permission is order 2 — it distorts. Political rhetoric that invokes "the law"
while stating no checkable rule is order 3 — it performs reference to a rule
whose content is absent (which is why 0.3% of party-leader speech made a
checkable claim, and why the debate tools are a *screen*, not the metric). And a
rule that exists only as generated text — the recursive LLM rewrite whose parent
is another generation, never an enacted source — is order 4: a norm that never
had an original. That is where the project's name comes from.

**Simulacria** is the engine and method (the recursive loop, the measurement, the
lineage). **Allegoria** is the most extreme transform — allegory swaps the entire
reference domain in one step, so it is the fastest route from territory to
simulacrum, and the sharpest instrument for seeing what survives.

---

## What the metric actually measures, in these terms

The contribution is not "representations drift from their referent" — that is
Baudrillard's premise. It is that **the drift has a sign, and the sign is
recoverable**. The distance between map and territory is not a scalar. A
description can drift by *loosening* (the permitted set grows — a *safety* error,
the sign grants what the source withheld) or by *tightening* (it shrinks — a
*fidelity* error, the sign forbids what the source allowed). Baudrillard has no
apparatus for this direction; similarity metrics (cosine, BLEU) collapse it,
because the two directions sit equally far from the source in meaning-space. The
signed deontic metric is precisely the apparatus that recovers which order-2
distortion occurred, and in which direction.

So the engine is a **measuring instrument for the second and third orders**: it
quantifies how far, and which way, a restatement has departed from the norm it
claims to represent — and flags (as *unobservable*) the third-order case where
there is no checkable referent to depart from at all.

---

## The deontic grounding

The metric is only possible because normative language has an explicit modal
structure. It rests on **deontic logic** — the logic of obligation (O),
permission (P) and prohibition (F), formalised by G. H. von Wright (1951), with
the duality that the permitted is what is not forbidden. Loosening = the set of
permitted world-states grows; tightening = it shrinks. That single definition is
a deontic statement, not a stylistic one, which is why it can be signed
deterministically rather than judged.

Two vocabularies make the modality machine-readable, and the project uses both as
real corpora:

- **Swedish statute** — `ska` / `får` / `får inte` / `dock` mark duty, permission,
  prohibition and carve-out explicitly.
- **IETF RFC 2119** — `MUST` / `SHOULD` / `MAY` are an engineered deontic
  vocabulary: an obligation, a defeasible obligation, a permission. A requirement
  that moves `MUST → SHOULD` between spec versions is a deontic weakening, read
  without a model.

The four moving parts (duty, exception, ceiling, qualifier) and the determinacy
ladder (`specific → vague → absent`) are a small deontic type system: they say
*which* modal operator is in play and *what it attaches to*, which is what fixes
the sign of a change. The ladder also captures a subtler drift Baudrillard would
recognise — force draining out of a rule before its words vanish ("within a
reasonable time" still looks like a condition but can no longer be tested).

---

## The semantics: why the sign is the content

Distributional semantics (embeddings) places meaning by context of use, so
"...provided compensation is given" and the same clause with that condition
removed sit almost on top of each other — nearly identical contexts, near-maximal
cosine similarity. Yet their **truth conditions** differ totally: one permits an
act only under a condition, the other permits it unconditionally. The project's
stance is that for normative text the meaning that matters is *model-theoretic*
(which world-states the rule permits), not distributional (which words tend to
co-occur). The signed metric measures the model-theoretic shift; embeddings are
kept only as a descriptive companion for surfacing anomalies, never as the source
of truth. In Baudrillard's terms: a similarity score cannot tell a faithful
reflection from a distortion, because in sign-space they look the same. The whole
point is to leave sign-space and ask what the norm now permits.

---

## Where the philosophy meets the results

- **Real institutional drift** (RFC version chains, `normative_drift.json`): a
  norm restated by its own authors across decades. The cookie spec's requirement
  posture loosened markedly (MUST share 42% → 28%); TLS held strict. This is
  order-1-to-order-2 drift, signed, on real data — no model needed.
- **Description vs rule** (Swedish law): whether a restatement preserves the
  deontic structure of the provision it cites — order 1 vs order 2, per slot.
- **Reference without a referent** (party-leader debate): overwhelmingly order 3
  — the word "law" invoked with no checkable rule attached, which the metric
  honestly reports as unobservable rather than scoring.

The instrument does not decide whether drift is good. Loosening is not freedom
and tightening is not safety; the sign describes the scope of permitted action,
nothing more. What it offers is the one thing the theory of simulacra names but
does not measure: the direction in which a copy has left its original.

---

### Sources consulted
- Jean Baudrillard, *Simulacra and Simulation* (1981; Glaser trans. 1994) — the
  four orders and the precession of simulacra.
- G. H. von Wright, "Deontic Logic," *Mind* (1951) — the modal logic of O/P/F.
- IETF RFC 2119 / RFC 8174 — the MUST/SHOULD/MAY requirement vocabulary.
- See `IDEA.md` for the research premise and `DIRECTION.md` for the metric.
