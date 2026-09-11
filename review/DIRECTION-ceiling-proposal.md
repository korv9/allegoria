# Proposed: add `ceiling` to DIRECTION.md

**Status: PROPOSAL. `DIRECTION.md` is unchanged.** This is a specification
change, so it waits for ratification. Nothing in the code classifies ceilings;
`scripts/write_specimens.py` only flags the pattern as `ceiling?` for hand
resolution.

---

## Why

Three specimens on the previous sheet were labelled `exception` and are not
exceptions:

| Specimen | Text |
| --- | --- |
| `sfs-2026-786:K10P20` | "dock **längst under 48 timmar**" |
| `sfs-2026-1283:K2P6` | "dock **under högst tre år**" |
| `sfs-2026-1601:K6P8` | "dock **högst fyra veckor**" |

Each bounds how far a granted power reaches. None removes cases from a duty.
The distinction inverts the sign, so filing one as the other makes the
derivation rule return the wrong answer:

| Part | What removal does | Sign |
| --- | --- | --- |
| Exception to a duty | the duty reaches more cases | `tightening` |
| Ceiling on a permission | the permission becomes unbounded | `loosening` |

`dock` is the trap: one marker, two structural functions.

---

## Proposed diff

### 1. In "The three parts"

```diff
 A provision that can express direction has up to three moving parts:

 1. **Duty** — what shall or shall not happen
 2. **Exception** — a carve-out from the duty
-3. **Qualifier** — a condition attached to either the duty or the exception
+3. **Ceiling** — an upper bound on how far a granted power reaches
+4. **Qualifier** — a condition attached to the duty, the exception or the ceiling

 The qualifier is the interesting one, because **which part it hangs on
 determines the sign of its removal.**
+
+A ceiling is not an exception, and the difference is not cosmetic. Removing an
+exception makes a duty reach further and is `tightening`. Removing a ceiling
+leaves every case inside the permission and lifts the limit on its extent,
+which is `loosening`. Both are commonly written with `dock`.
```

### 2. In "The derivation rule"

```diff
 | Parent modality | Qualifier weakened | Qualifier strengthened |
 |---|---|---|
 | **Binding** (`ska`, `får inte`) | tightening | loosening |
 | **Enabling** (`får`, exception) | loosening | tightening |
+| **Ceiling** (`dock längst`, `högst`) | loosening | tightening |
+
+And for removal of a whole part, which the table above does not cover:
+
+| Part removed | Sign |
+|---|---|
+| Exception, duty intact | tightening |
+| Ceiling, permission intact | loosening |
+
+The ceiling row reads the same as the enabling row, and that is expected: both
+widen a permission when weakened. The reason `ceiling` must still be its own
+part is the removal table. An annotator who files a ceiling under `exception`
+gets the opposite sign the moment the part disappears entirely — which is the
+generation the experiment is watching for.
```

### 3. In "Slot kinds"

```diff
 - `actor` — who the norm governs
 - `deadline` — a time limit
 - `condition` — a qualifier or precondition
+- `bound` — an upper limit on quantity, duration or extent of a permission
 - `modality` — the deontic operator itself (`ska` → `bör` is a weakening)

-Each slot records: kind, the part it attaches to (`duty` or `exception`), and
-its determinacy state.
+Each slot records: kind, the part it attaches to (`duty`, `exception` or
+`ceiling`), and its determinacy state. A ceiling has a determinacy state of its
+own — "dock längst 48 timmar" is `specific`, "dock endast en kortare tid" is
+`vague` — and moves on the same ladder.
```

### 4. In "Test cases" — additions only, 1–9 unchanged

```diff
 | 9 | Qualifier on exception dropped **and** actor on duty narrowed | `(1, 1, 0)` — not `neutral` |
+| 10 | Ceiling removed entirely, permission intact | `loosening` |
+| 11 | Ceiling weakened: `specific` → `vague` ("dock längst 48 timmar" → "dock endast en kortare tid") | `loosening` |
+| 12 | Ceiling strengthened: `vague` → `specific` fixing a shorter cap | `tightening` |
+| 13 | Qualifier on a ceiling: `specific` → `absent`, so the cap applies in fewer cases | `loosening` |
+| 14 | The same sentence read both ways: exception removed vs ceiling removed | `tightening` vs `loosening` — must not agree |

 Case 9 is the regression test for the netting decision. If it ever returns
 `neutral`, the metric has stopped being able to express the finding the project
 exists to study.
+
+Case 14 is the regression test for this category. If a ceiling and an exception
+ever classify the same way, `ceiling` has stopped doing any work.
```

---

## The discriminating test, for hand annotation

Apply in order. The first question usually settles it.

**1. What does the `dock` clause interrupt — an obligation or a grant?**
Look at the modality of the clause the `dock` qualifies. `ska`, `ska inte`,
`får inte`, `är skyldig` is binding, and a `dock` attached to it is usually an
exception. `får`, `har rätt att`, `kan` is enabling, and a `dock` attached to it
is usually a ceiling.

**2. Does the clause remove situations, or cap magnitude?**
An exception answers *in which cases does the rule not apply?* A ceiling answers
*how much, how long, how far?* A ceiling leaves the rule applicable in every
case it already covered.

**3. The operative test — delete the clause and read what remains.**

- If the main rule now applies to **more situations** → it was an exception.
- If the same situations apply but with **no limit on duration, quantity or
  extent** → it was a ceiling.

On `sfs-2026-786:K10P20`, deleting "dock längst under 48 timmar" leaves the
police able to detain in exactly the same circumstances, for unlimited time.
Nothing changed about *when*; everything changed about *how long*. Ceiling.

---

## Boundary cases I am not sure about

These are the ones to argue about before ratifying. I have not smoothed them.

**(a) A bound inside an exception's condition.** `sfs-1982-80:P28`:
"Beskedet behöver **dock inte** lämnas, om anställningstiden är **högst en
månad**." The `dock` introduces a genuine exception; "högst en månad" is a
qualifier *inside* it. Proposed reading: exception + qualifier, not a ceiling.
The bound word is present but is not doing ceiling work.

**(b) Floors, and preconditions on timing.** `sfs-2026-772:K1P4`: "Den tidigare
hyran måste **dock ha gällt i minst ett år**." This bounds *when* a power may be
exercised, not how far it extends. Removing it lets the power be used sooner,
which is `loosening` — the same sign as removing a ceiling, by a different
mechanism. Is this a ceiling with reversed polarity, or a qualifier on the duty?
I do not know, and the sign coinciding means we can defer it without immediate
cost.

**(c) Hedged bounds.** `sfs-1977-480:P11`: "dock **om möjligt** minst en månad
före". A bound softened by "om möjligt" is already vague at birth. If it is a
ceiling, it starts on the middle rung and can only fall once.

**(d) Non-temporal ceilings.** `sfs-1982-80:P25a`: "dock **högst heltid**". The
category must not be defined as temporal — this one is measured in extent of
employment. `sfs-1982-673:P8` bounds overtime at "högst 200 timmar under ett
kalenderår", which is a quantity per period.

**(e) Deadlines on duties that happen to use `dock`.** `sfs-1982-80:P6c`: "dock
**senast** den sjunde kalenderdagen". This is a deadline qualifier on a duty,
not a ceiling on a power. Worth noting that removing it is `loosening` too, so
confusing (e) with a ceiling costs nothing in sign — whereas confusing a ceiling
with an *exception* costs everything. If annotation time is scarce, spend it on
the exception/ceiling call and not on this one.

---

## How big the category is

Measured with `scripts/audit_markers.py ceiling-scan`:

| Pool | Candidates | Carry `dock` | Carry `dock` + a bound |
| --- | ---: | ---: | ---: |
| v1 | 461 | 155 | **17** (11.0% of `dock` candidates) |
| v2 | 4071 | 1109 | **137** (12.4%) |

I read all 17 v1 flags. **9 are true ceilings**; 8 are a bound word doing
another job — cases (a), (b) and (e) above. So the flag runs at roughly 53%
precision on v1 and is a screening aid, not a classifier. Extrapolating the same
rate, v2 holds on the order of 70 real ceilings, but that is `[inferred]` — I
read the v1 flags, not the v2 ones.

Either way the category is small in absolute terms and concentrated: roughly one
candidate in 30 carries a ceiling. It is cheap to annotate by hand and there is
no case for automating it.
