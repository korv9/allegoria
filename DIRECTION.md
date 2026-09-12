# DIRECTION.md

The specification for `direction` — the core metric. Read this before touching
anything in `simulacria/measurement/direction.py`.

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

## The four parts

A provision that can express direction has up to four moving parts:

1. **Duty** — what shall or shall not happen
2. **Exception** — a carve-out from the duty
3. **Ceiling** — an upper bound on how far a granted power reaches
4. **Qualifier** — a condition attached to the duty, the exception or the ceiling

The qualifier is the interesting one, because **which part it hangs on
determines the sign of its removal.**

This is annotated by hand during corpus construction. It is never inferred at
measurement time.

A ceiling is not an exception, and the difference is not cosmetic. Removing an
exception makes a duty reach further and is `tightening`. Removing a ceiling
leaves every case inside the permission and lifts the limit on its extent,
which is `loosening`. Both are commonly written with `dock`.

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
| **Ceiling** (`dock längst`, `högst`) | loosening | tightening |

Read it as: weakening a condition on a duty makes the duty apply more broadly
(tightening). Weakening a condition on an exception makes the escape hatch
easier to use (loosening).

For removal or insertion of a whole part, which the table above does not cover:

| Whole-part change | Sign |
|---|---|
| Exception removed, duty intact | tightening |
| Ceiling removed, permission intact | loosening |
| Exception inserted where none existed, duty intact | loosening |
| Ceiling inserted where none existed, permission intact | tightening |

The ceiling row reads the same as the enabling row, and that is expected: both
widen a permission when weakened. The reason `ceiling` must still be its own
part is the removal table. An annotator who files a ceiling under `exception`
gets the opposite sign the moment the part disappears entirely — which is the
generation the experiment is watching for.

---

## Distinguishing ceilings from exceptions during hand annotation

Apply these questions in order. A marker is a screening aid, never the answer.

**1. What does the `dock` clause interrupt — an obligation or a grant?**
Look at the modality of the clause it qualifies. `ska`, `ska inte`, `får inte`
and `är skyldig` are binding: an attached `dock` is usually an exception.
`får`, `har rätt att` and `kan` are enabling: an attached `dock` is usually a ceiling.

**2. Does the clause remove situations, or cap magnitude?**
An exception answers *in which cases does the rule not apply?* A ceiling answers
*how much, how long, how far?* A ceiling leaves the rule applicable in every
case it already covered.

**3. Delete the clause and read what remains.**

- If a duty now applies to **more situations**, the removed part was an exception.
- If a power can now be exercised in **more situations**, the removed clause was
  a condition on its applicability; this does not establish a ceiling.
- If the same situations apply but with **no limit on duration, quantity or
  extent**, the removed part was a ceiling.

On `sfs-2026-786:K10P20`, deleting "dock längst under 48 timmar" leaves the
permission, in this isolated-clause comparison, applicable in the same
circumstances with its stated duration cap removed. Nothing changed about
*when*; the change concerns *how long*. Ceiling.

### Boundary cases

**(a) A bound inside an exception's condition.** `sfs-1982-80:P28`:
"Beskedet behöver dock inte lämnas, om anställningstiden är högst en månad."
The `dock` introduces an exception; "högst en månad" is a qualifier inside it,
not a ceiling. A bound word does not by itself identify a ceiling.

**(b) Floor / timing precondition — resolved.** `sfs-2026-772:K1P4`:
"Den tidigare hyran måste dock ha gällt i minst ett år."
Deleting the clause allows the power to be exercised sooner, in more situations,
rather than extending its magnitude in the same situations. The ratified
annotation is **qualifier on the duty, not a ceiling**. No reversed-polarity
ceiling category is introduced.

**(c) Hedged bounds.** `sfs-1977-480:P11`: "dock om möjligt minst en månad före".
The bound is softened by "om möjligt" and is already vague. If classified as
a ceiling after hand review, it starts on the middle rung of the ladder.
Its attachment still requires review; the wording alone does not settle it.

**(d) Non-temporal ceilings.** `sfs-1982-80:P25a`: "dock högst heltid" limits
extent of employment. `sfs-1982-673:P8`: "högst 200 timmar under ett kalenderår"
limits quantity per period. The category is not restricted to duration.

**(e) Deadlines on duties.** `sfs-1982-80:P6c`: "dock senast den sjunde
kalenderdagen" is a deadline qualifier on a duty, not a ceiling on a power.
The proposal describes its removal as `loosening`; its relationship to the
binding-qualifier row needs to be made explicit before encoding this boundary
case. Ratifying `ceiling` does not silently resolve that distinction.

### Screening precision, not annotation authority

The historical v1 `ceiling?` screen flagged **17** candidates; hand-reading
identified **9 true ceilings**, roughly **53% precision**. Roughly every second
flag was therefore wrong: treat it as a question to resolve, not a suggested
label to confirm. The flags must never feed the metric directly.

The v2 screen flagged 137 candidates. Extrapolating the v1 precision suggests
about 70 true ceilings **[inferred]**; that is not a hand-reviewed v2 count.
The original evidence and reasoning remain in
[`review/2026-09-11/DIRECTION-ceiling-proposal.md`](review/2026-09-11/DIRECTION-ceiling-proposal.md).

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

**Never net them out.** If a qualifier on an exception dies (loosening) while
the actor on a duty broadens (tightening), netting yields zero — "nothing happened" — when in fact
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
- `bound` — an upper limit on quantity, duration or extent of a permission
- `modality` — the deontic operator itself (`ska` → `bör` is a weakening)

Each slot records: kind, the part it attaches to (`duty`, `exception` or
`ceiling`), and its determinacy state. A ceiling has a determinacy state of its
own — "dock längst 48 timmar" is `specific`, "dock endast en kortare tid" is
`vague` — and moves on the same ladder.

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
| 9 | Qualifier on exception dropped **and** actor on duty **broadened** | `(1, 1, 0)` — not `neutral` |
| 9b | Qualifier on exception dropped **and** actor on duty narrowed | `(0, 2, 0)` |
| 10 | Ceiling removed entirely, permission intact | `loosening` |
| 11 | Ceiling weakened: `specific` → `vague` ("dock längst 48 timmar" → "dock endast en kortare tid") | `loosening` |
| 12 | Ceiling strengthened: `vague` → `specific` fixing a shorter cap | `tightening` |
| 13 | Qualifier on a ceiling: `specific` → `absent`, so the cap applies in fewer cases | `loosening` |
| 14 | The same sentence read both ways: exception removed vs ceiling removed | `tightening` vs `loosening` — must not agree |

Case 7 stays `loosening`: narrowing "arbetsgivare" to "statlig arbetsgivare"
releases private employers from the duty, so permitted world-states grow.
Conversely, case 9 broadens "Statlig arbetsgivare ska X" to "Arbetsgivare ska X":
more parties are bound and permitted world-states shrink (`tightening`).

Case 9 is the regression test for the netting decision. If it ever returns
`neutral`, the metric has stopped being able to express the finding the project
exists to study.

Case 9b is the regression test for multiplicity: two changes with the same sign
must remain two counts, not collapse into one ternary label.

Case 14 is the regression test for this category. If removing a ceiling and
removing an exception ever classify the same way, `ceiling` has stopped doing
any work. Cases 1–14 plus supplementary case 9b make fifteen table entries.

---

## Status of these definitions

**Ratified 2026-09-12 in the specification commit recording DD051 and DD052:**
the case 9 correction, supplementary case 9b, and `ceiling` with the four
user-requested amendments (floor ruling, insertion rows, screening precision,
and retention of case 14). The historical proposal is retained as resolved.

This ratifies the specification changes, not any corpus annotation, model
reading or implementation. Part 3 prepares a human-review packet; implementation
must follow this specification commit. Any ambiguity encountered while encoding
the table must be reported rather than resolved by the implementer.

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
