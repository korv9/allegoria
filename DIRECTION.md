# DIRECTION.md

The specification for `direction` — the core metric. Read this before touching
anything in `simulacria/direction.py`.

Prose is English; all example text stays Swedish, because the metric depends on
Swedish deontic markers (`ska`, `får`, `får inte`, `dock`).

---

## The one definition

> **Loosening = the set of permitted world-states grows.
> Tightening = it shrinks.**

Everything below is a consequence of this. When two people disagree about a
classification, the appeal is to this sentence, not to intuition.

Concretely, for any provision, ask one question:

**After the change, is it easier or harder to do the thing?**

Easier → `loosening`. Harder → `tightening`. Neither → `neutral`.

---

## What the metric is not

`direction` measures the **scope of permitted action**, not who benefits and not
whether the change is good.

In the worked example below, a provision loosens — and the party who loses out
is the citizen whose dispute no longer gets heard. Loosening is not a synonym
for "more freedom for people" or "worse outcome". It is a statement about how
much room the norm leaves for the actor it governs.

State this explicitly wherever results are presented. Readers will otherwise
import a normative reading that the metric does not carry.

---

## The three parts

A provision that can express direction has up to three moving parts:

1. **Duty** — what shall or shall not happen
2. **Exception** — a carve-out from the duty
3. **Qualifier** — a condition attached to either the duty or the exception

The qualifier is the interesting one, because **which part it hangs on
determines the sign of its removal.**

This is annotated by hand during corpus construction. It is never inferred at
measurement time.

---

## Worked example — real SFS text

From `data/bronze/sfs/`, Elmarknadslag (2026:1281) 10 §:

> Nätmyndigheten **ska** ta upp en tvist om vilka kostnader som ska debiteras
> enligt 6, 7 eller 9 §.
>
> En tvist **ska dock inte** prövas om ansökan om prövning har kommit in till
> nätmyndigheten **senare än två år** efter det att den systemansvariga skickat
> ett skriftligt ställningstagande till den berörda partens senaste kända
> adress.

Decomposition:

| # | Part | Text | Attaches to |
|---|---|---|---|
| 1 | duty | myndigheten ska pröva tvisten | — |
| 2 | exception | ska dock inte prövas | the duty |
| 3 | qualifier | om ansökan kommit in senare än två år | the **exception** |

### Case A — the qualifier is dropped

> Nätmyndigheten ska ta upp en tvist. En tvist ska dock inte prövas.

Before, the authority could decline only after the two-year deadline had passed.
Now it can decline always. The exception has swallowed the rule.

→ **`loosening`**

### Case B — a qualifier on the *duty* is dropped

Remove "enligt 6, 7 eller 9 §" from part 1:

> Nätmyndigheten ska ta upp en tvist om vilka kostnader som ska debiteras.

Now every cost dispute must be heard, not only those under three specified
sections. The duty reaches further.

→ **`tightening`**

Cases A and B are the *same operation* — a qualifier disappears — with opposite
signs. The only difference is what the qualifier was attached to.

---

## The derivation rule

| Parent modality | Qualifier weakened | Qualifier strengthened |
|---|---|---|
| **Binding** (`ska`, `får inte`) | tightening | loosening |
| **Enabling** (`får`, exception) | loosening | tightening |

Read it as: weakening a condition on a duty makes the duty apply more broadly
(tightening). Weakening a condition on an exception makes the escape hatch
easier to use (loosening).

---

## The determinacy ladder

Qualifiers rarely vanish outright. They go vague first.

| State | Example |
|---|---|
| `specific` | "senare än två år", "inom sju dagar" |
| `vague` | "efter lång tid", "skyndsamt", "inom skälig tid" |
| `absent` | — |

Moving down the ladder is `weakened`; moving up is `strengthened`.

A vague qualifier is still a qualifier, but it cannot be tested — nobody can say
whether "lång tid" has been exceeded, while two years is checkable. The force
has drained out before the words have.

**Binary present/absent bookkeeping would register nothing until the qualifier
disappears entirely, missing the generation where the interesting thing
happened.** The ladder exists for this reason.

---

## Reporting shape

**Per slot:** ternary — `tightening` / `loosening` / `neutral`. Not a continuous
scale; there is no theory that justifies calling one qualifier death "0.7
loosening", and a reviewer will reject the false precision.

**Per passage:** a count vector, never a net.

```
(n_tightening, n_loosening, n_neutral)
```

**Never net them out.** If a qualifier dies (loosening) while an actor clause
narrows (tightening), netting yields zero — "nothing happened" — when in fact
two things happened and one of them widened a permission. The original
qualifier-death finding would have been invisible under netting.

There is a deeper reason not to sum them: they are not mirror images.

- A rule that becomes **stricter** than its source is a *fidelity* error. The
  system is more cautious than it should be.
- A rule that becomes **more permissive** than its source is a *safety* error.
  The system grants permissions the original does not.

The headline curve should therefore be **`loosening_count` per generation**.
Tightening is reported alongside, never subtracted.

---

## No slot weights

The temptation to weight qualifiers more heavily comes from a correct
observation with a wrong diagnosis. The qualifier is not worth more — it sits in
a different structural position, and position already determines the sign via
the derivation rule above.

Weights would introduce a free parameter with no defence ("why 2.0?"). If the
data later shows qualifiers dominate, **stratify results by slot kind** instead.
Same information, zero free parameters.

---

## Slot kinds

- `actor` — who the norm governs
- `deadline` — a time limit
- `condition` — a qualifier or precondition
- `modality` — the deontic operator itself (`ska` → `bör` is a weakening)

Each slot records: kind, the part it attaches to (`duty` or `exception`), and
its determinacy state.

---

## Test cases

These should be unit tests before any API call is made. All are derivable by
hand from text already in the repo.

| # | Change | Expected |
|---|---|---|
| 1 | Qualifier on exception: `specific` → `absent` | `loosening` |
| 2 | Qualifier on duty: `specific` → `absent` | `tightening` |
| 3 | Qualifier on exception: `specific` → `vague` | `loosening` |
| 4 | Qualifier on exception: `vague` → `absent` | `loosening` |
| 5 | Exception removed entirely, duty intact | `tightening` |
| 6 | `ska` → `bör` on the duty | `loosening` |
| 7 | Actor narrowed on the duty ("arbetsgivare" → "statlig arbetsgivare") | `loosening` |
| 8 | Pure rewording, all slots intact at same determinacy | `neutral` |
| 9 | Qualifier on exception dropped **and** actor on duty narrowed | `(1, 1, 0)` — not `neutral` |

Case 9 is the regression test for the netting decision. If it ever returns
`neutral`, the metric has stopped being able to express the finding the project
exists to study.

---

## Status of these definitions

Proposed and argued through in session, **not yet ratified in
`DATA_DECISIONS.md`**. Implement against them, but flag to Anton rather than
treating them as settled if an edge case forces a change.

The four questions they answer were:

1. Ternary or scale? → ternary per slot, vector per passage
2. Net or separate? → separate, always
3. Slot weights? → none; stratify instead
4. Altered vs removed? → the determinacy ladder

---

## Reproducibility gap

The founding observation — that a compensation qualifier on a rest-period
exception died before the exception itself — was seen in a run that left **no
artifact in this repo**. No input, no output, no manifest.

Reproducing it under the loop, with a manifest, is the first result the project
needs. Until then the central finding is a memory, and the test suite above is
the only thing standing in for it.
