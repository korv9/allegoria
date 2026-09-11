# Review packet — 2026-09-11

Unattended run. Parts A–E are done; nothing in Phase 2 was touched and no LLM
was called. Every factual claim below carries an evidence tag: `[measured]` with
the script or query that produced it, `[read]` where I read the text and am
reporting what it says, `[inferred]` where I am reasoning from pattern without
checking directly.

The companion sheet is `review/SPECIMENS.md`.

---

## 1. Decisions I need from you

### Decision 1 — the `om inte` fix, which I did not ship

The prescribed fix does not survive contact with the data, so **the pattern is
unchanged in the repo** and this is the run's central open question.

| Option | Precision | Recall | Notes |
| --- | --- | --- | --- |
| **A. Leave as is** | 73.8% | 100.0% | Today's behaviour. 21 of 80 gold hits are spurious |
| **B. Allowlist, as specified** | 100.0% | **54.2%** | Trips your 5-point recall stop condition nine times over |
| **C. Allowlist widened** | 100.0% | **54.2%** | Identical. Widening buys literally nothing |
| **D. Tempered gap (recommended)** | 90.8% | 100.0% | +17.0 points of precision at zero recall cost — but uses a wildcard token class you banned |

`[measured]` — `python scripts/score_om_inte.py`, scored against the frozen
80-entry gold set in `tests/fixtures/om_inte_gold.yaml`.

**Why B fails.** The allowlist assumes intervening tokens are pronouns and
determiners. They mostly are not. The misses are ordinary lexical subject noun
phrases — `om arbetstagaren inte`, `om avgiften inte`, `om bostadsbyggnaden
inte`, `om ändringen inte` — an open class no enumeration can cover. `[read]`,
from the 27 false negatives in the gold set. That is why C scores identically to
B: I added every determiner and quantifier the gold set actually shows, and not
one false negative moved. `[measured]`

**What D is.** It keeps a gap but tempers it so it cannot cross `att`, `som`,
`men`, `vilket`, `där`, `när`, `då`, or sentence punctuation. It kills every
`om att` complement clause and every `som` relative clause while keeping
coordinated subjects like `om vapnet eller vapendelen inte`. `[measured]`

**Why I did not ship D.** It uses `[^\s,;:.!?]+`, a wildcard token class. You
said never to reintroduce `\w+`. D is materially different — it *cannot* match
the boundary tokens, which was the actual defect — but it is the same shape, and
overriding an explicit instruction is not something to do unattended.

**Projected effect if you approve D** `[measured]`,
`scripts/score_om_inte.py --project tempered_coord`:

- v1: 461 → 459 candidates, with **both** `sfs-2026-1054:P8` and
  `sfs-2026-485:P13` leaving, exactly as your predictions expected
- v2: 4071 → 4075 candidates (58 leave, 62 join — D also matches some genuine
  carve-outs the current pattern misses), and `specific` rises 837 → 847
- All 20 specimens in `SPECIMENS.md` survive D, so that sheet is safe either way

**My recommendation: D.** `find_candidates.py` is recall-tuned by design, and D
is the only option that raises precision without costing recall.

### Decision 2 — the fixture now fails, and I am not allowed to fix it

`tests/test_candidate_markers.py::test_fixture_provisions_hit_their_markers`
fails on one assertion:

```
sfs-2026-1283:K5P1: determinacy went unmarked -> specific
```

`[measured]`, `python -m pytest -q`. This is **caused by Part A4**, which you
asked for. The fixture pinned that provision precisely to keep the number-word
gap visible; closing the gap is what makes it fail. The provision still
surfaces and its markers are unchanged — only determinacy moved, and it moved to
the correct value.

Options: (a) update the fixture entry to `specific` and rewrite its note, which
is the honest outcome of an intended change; (b) revert A4. **I recommend (a)**,
but the fixture is frozen evidence and the rule says I do not edit it to make a
run green.

### Decision 3 — a parser bug that discards whole documents

`sfs-2023-692` carries ten well-formed paragraphs, `1 §` through `10 §`, and is
discarded entirely. `[read]` `_transitional_records` requires an SFS marker as a
bare number alone on a line; this law writes it `SFS 2023:692` with the prefix
inline. A trailing section the parser cannot split destroys every paragraph in
the document.

**v1 is measurably unaffected** `[measured]`: 23 of the 50 v1 documents have a
transitional section, the strict regex finds all 76 markers in them — exactly
the 76 `transitional_provision` rows in Silver — and no v1 document uses the
inline form. So this is latent exposure, not silent loss inside the 1,952. That
is why I did not stop the run.

The fix is one optional `SFS\s+` prefix and dropping the line-anchoring, but
`sfs_parser.py` is shared with the Databricks Silver notebook and governs the
frozen v1 counts, so I left it. Recorded as DD042.

### Decision 4 — a latent break in the Databricks Silver notebook

`bronze_sfs.py` persists the column as `bronze_ingested_at`; `silver_sfs.py`
selects `ingested_at`. `[read]`, both files. Against a real Bronze table Silver
would fail to resolve the column. This came in with commit 4da6517, and
`tests/test_allegoria_product.py` now asserts the changed form, so the test
pins the defect. Out of scope to fix here; recorded in DD041.

### Decision 5 — a labelling policy in the gold set

Four gold entries are concessive `även om ... inte` ("applies even if X does
not"), which is syntactically identical to a carve-out but pragmatically
*extends* a rule rather than carving out of it. I labelled them `conditional`
and said so in the file header, because the regex is a marker detector and
`DIRECTION.md` gives the carve-out judgment to hand annotation. If you disagree,
the labels change in `scripts/write_om_inte_gold.py` and the file is
regenerated — never edited in place. `[read]`

---

## 2. Predictions with known answers

| # | Prediction | Result |
| --- | --- | --- |
| 1 | All 12 pinned provisions still surface | **PASS** |
| 1b | …with unchanged marker coverage | **PASS** |
| 1c | …with unchanged determinacy | **FAIL** — `sfs-2026-1283:K5P1`, `unmarked → specific`, caused by A4 |
| 2 | v1 rank 2 (`sfs-2026-1054:P8`) no longer qualifies | **FAIL** — still a candidate; no fix shipped |
| 3 | v1 rank 11 (`sfs-2026-485:P13`) no longer qualifies | **FAIL** — still a candidate; no fix shipped |
| 4 | v1 counts still 50 / 1952, assertions unrelaxed | **PASS** |

Predictions 2 and 3 fail because Decision 1 was not mine to make. Under option
D both hold. `[measured]`

---

## 3. What changed

### Scorecards, `om inte`

`[measured]`, `scripts/score_om_inte.py`, frozen gold set of 80 hits
(59 conditional, 21 spurious):

| pattern | TP | FP | FN | TN | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current (shipped) | 59 | 21 | 0 | 0 | 73.8% | 100.0% | 0.849 |
| allowlist | 32 | 0 | 27 | 21 | 100.0% | 54.2% | 0.703 |
| widened | 32 | 0 | 27 | 21 | 100.0% | 54.2% | 0.703 |
| tempered | 55 | 4 | 4 | 17 | 93.2% | 93.2% | 0.932 |
| **tempered_coord** | 59 | 6 | 0 | 15 | **90.8%** | **100.0%** | **0.952** |

One caveat that matters for reading these: the gold set was sampled from the
*current* pattern's own hits, so a genuine carve-out today's pattern never
matched cannot appear in it. The current row's recall of 100% is construction,
not merit, and the set can measure precision gains and recall losses but not
recall gains. `[measured]` The set is also deliberately enriched with hard
cases, so its precision figures are lower bounds, not corpus estimates.

### Corpus deltas over the whole run

`[measured]`, `scripts/build_silver.py`, `scripts/build_tables.py`,
`scripts/query.py`:

| | v1 before | v1 after | v2 before | v2 after |
| --- | ---: | ---: | ---: | ---: |
| Provisions | 1952 | **1952** | 18836 | **18836** |
| Candidates | 460 | 461 | 4057 | 4071 |
| `determinacy = specific` | 114 | 119 | 819 | 837 |
| …as % of candidates | 24.8% | 25.8% | 20.2% | 20.6% |
| Specific and under 400 chars | — | 29 | — | 142 |
| Documents with zero candidates | 6 | 5 | — | — |

Every change comes from A4 (number words through "hundra") and B5
(`i den utsträckning`). No provision left either candidate set; v1 gained
`sfs-2026-456:P2`, the near-miss that motivated B5, and v2 gained 14.

Determinacy rungs changed on 9 of 1952 v1 provisions and 31 of 18836 v2
provisions, all upward to `specific`. `[measured]`,
`scripts/audit_markers.py determinacy-delta`. **Caveat worth your attention:**
the single most common newly-matched token is `arton år` — 3 in v1, 18 in v2 —
which is an *age threshold*, not a deadline. The `specific` floor rose, but not
all of the rise is deadlines. `[read]`

### Top 15, v1 (after)

`[measured]`. Position changes against the pre-run ranking in brackets.

| # | Provision | Change |
| --- | --- | --- |
| 1 | sfs-2026-585:P18 | = |
| 2 | sfs-2026-1054:P8 | = *(rests on a spurious hit; leaves under D)* |
| 3 | sfs-1977-480:P11 | = |
| 4 | sfs-2026-1283:K5P1 | = *(the A4 determinacy flip)* |
| 5 | sfs-1982-80:P10 | = |
| 6 | sfs-1982-80:P20 | = |
| 7 | sfs-1977-480:P19 | = |
| 8 | sfs-1982-80:P18 | = |
| 9 | sfs-2026-786:K5P2 | = |
| 10 | sfs-2026-408:K9P10 | = |
| 11 | sfs-2026-1011:K6P8 | = |
| 12 | sfs-1982-673:P3 | **+14** (was 26) — gained `i den utsträckning` |
| 13 | sfs-2026-1283:overgang:2026-1283 | −1 |
| 14 | sfs-1977-480:P12 | −1 |
| 15 | sfs-2026-485:P13 | −1 *(rests on a spurious hit; leaves under D)* |

### Top 15, v2 (after)

`[measured]`. Ranks 1–15 are unchanged in order from the pre-run ranking.

| # | Provision | Change |
| --- | --- | --- |
| 1 | sfs-2022-260:K5P2 | = |
| 2 | sfs-2022-964:K4P16 | = |
| 3 | sfs-2015-953:P17 | = |
| 4 | sfs-2026-585:P18 | = |
| 5 | sfs-2022-964:K5P5 | = |
| 6 | sfs-2020-548:P19 | = |
| 7 | sfs-2018-1219:K9P8 | = |
| 8 | sfs-2024-237:P2 | = |
| 9 | sfs-2014-836:P15 | = |
| 10 | sfs-2025-1506:K2P12 | = |
| 11 | sfs-2022-700:K5P29 | = |
| 12 | sfs-2017-527:P8 | = |
| 13 | sfs-2018-672:K17P14 | = |
| 14 | sfs-2015-1016:K27P17 | = |
| 15 | sfs-2023-474:P10 | = |

### Where `sfs-2026-1281:K10P10` now ranks

`[measured]` — v1: **43** (was 39 pre-run, 43 after A4). v2: **272** (was 254
pre-run, 263 after A4). It did not get worse; provisions above it gained
`specific` and corroborating qualifier markers.

---

## 4. The v2 verdict

**Better specimens *and* more of them — but at roughly half the density, and
the top of the list is not where the dilution is.**

The prior read was "different in kind at the top, dilution below". Re-examined
with the spurious-hit question asked directly, that holds, and the "kind" half
is now measured rather than asserted.

**The apparent richness at the top of v2 is not spurious.** `[measured]`, by
swapping in the proposed fix and recomputing candidacy:

| | would lose candidacy under the fix | rest on `om inte` alone |
| --- | ---: | ---: |
| v1 top-15 | **2 of 15 (13%)** | 3 |
| v1 top-50 | 2 of 50 | 11 |
| v2 top-15 | **0 of 15 (0%)** | 3 |
| v2 top-50 | 1 of 50 (2%) | 12 |

v2's top 15 loses nothing to the defect; v1's loses two, at ranks 2 and 15. So
the larger pool's best specimens are *cleaner* than the small pool's, not merely
more numerous. That is a stronger result than the prior read claimed.

**The dilution is real and is in the density, not the quality.** `[measured]`:

| | v1 | v2 |
| --- | ---: | ---: |
| Provisions | 1,952 | 18,836 |
| Candidates | 461 (23.6% of provisions) | 4,071 (21.6%) |
| `specific` | 119 (25.8% of candidates) | 837 (20.6%) |
| Specific **and** under 400 chars | 29 | 142 |
| …per 1,000 provisions | **14.9** | **7.5** |

v2 yields 4.9× as many workable specimens from 9.6× as much text. Half the
density, five times the material.

**What that means for the work.** The pool earned its keep, for one reason more
than any other: the specimen sheet draws 20 specimens from 19 statutes without
strain. From v1 alone, 29 eligible specimens across a handful of laws would have
forced either repetition or a drop in quality. `[inferred]` — I did not build
the v1-only sheet to confirm the counterfactual.

The honest qualification: nothing here shows v2 is better *per specimen* than
v1 once you are past the top 50. The case for it is coverage and freedom to
stratify, not a higher hit rate.

---

## 5. Claims and how each was verified

Everything above is tagged inline. The consolidated list, so you can pick what
to spot-check:

**`[measured]` — a number produced by code**

| Claim | Produced by |
| --- | --- |
| Scorecards for all five patterns | `scripts/score_om_inte.py` |
| Projected candidate-set effect of the fix | `scripts/score_om_inte.py --project tempered_coord` |
| Determinacy rungs: 9 of 1952 v1, 31 of 18836 v2 | `scripts/audit_markers.py determinacy-delta --pool {v1,v2}` |
| Wildcard marker inventory and crossing rates | `scripts/audit_markers.py wildcard-inventory` |
| Candidate, specific and under-400 counts, both pools | `scripts/query.py --pool {v1,v2}` |
| Top-15 lists and rank movements | `scripts/query.py`, against `review/evidence/baseline_*_candidates.txt` |
| v1 still 50 documents / 1952 provisions | `scripts/build_silver.py`, assertions unrelaxed |
| v1 transitional markers: 76 found across 23 documents, 0 inline-form | ad-hoc script, output quoted in DD042 |
| Zero-`§` criterion catches 28 of 30 and no parsed document | ad-hoc script, output quoted in DD042 |
| All 20 specimens survive the proposed fix | ad-hoc script over `shortlist()` with the pattern swapped |
| Gold set composition: 59 conditional, 21 spurious | `scripts/write_om_inte_gold.py` |
| `i den utsträckning`: 43 hits over 39 v1 provisions | `scripts/query.py` against `marker_hits` |

**`[read]` — I read the text and am reporting what it says**

- All 80 gold entries, labelled individually with syntactic grounds
- `sfs-2018-1433` is a one-sentence repealing act with no `§` at all
- `sfs-2015-136` is a treaty act: one operative Swedish sentence, 34 KB of annex
  in `Artikel` form
- `sfs-2023-692` has 10 valid paragraphs and writes its SFS marker inline
- `sfs-2014-1475` is a repealed law served without anchors, announcing itself
  with `Har upphävts genom lag (2024:401)`
- The `bronze_ingested_at` / `ingested_at` mismatch, in both notebooks
- 20 sampled hits each for `får inte` and `undantag`
- All 20 specimens, including the quoted parts in `SPECIMENS.md`, which the
  renderer additionally asserts are verbatim substrings
- The false-negative spans that sink the allowlist option

**`[inferred]` — reasoning from pattern, not checked directly**

- That v1-only would have forced repetition in the specimen sheet — I did not
  build the counterfactual sheet
- That `undantag`'s participial uses ("undantagen från svensk skatt") are a
  semantic over-reach worth separating from the structural defect — I read the
  sampled contexts but did not label them against a gold standard
- That the four concessive `även om` entries are the only ones of their kind in
  the gold set — I classified them while labelling but did not search the corpus
  for the construction independently

---

## 6. What I could not verify

- **Corpus-wide precision of any pattern.** The gold set is deliberately
  enriched with hard cases, so its precision numbers are lower bounds. A
  uniform random sample would be needed for an unbiased estimate, and the
  stratification you specified rules that out for this set.
- **Recall gains.** The gold set cannot contain carve-outs the current pattern
  never matched, so I cannot tell you how many genuine `om inte` conditionals
  are missed corpus-wide today. The proposed fix matches 62 v2 provisions the
  current one does not, which suggests the current recall is below 100% in
  reality — but I cannot quantify it from this set.
- **Whether the transitional-marker bug causes *partial* loss inside v1.** I
  verified no v1 document fails outright and that all 76 markers are found. I
  did not verify that every transitional block is split at the right
  boundaries — a marker found in the wrong position would mis-split silently.
- **The 27 v2 laws I did not open.** Part D asked for three; I read four. The
  other 26 are classified by criterion, not by reading.
- **Whether `arton år` should count as `specific`.** It is checkable, so by the
  ladder's own definition it qualifies, but an age threshold is not a deadline
  and it now drives most of the v2 determinacy increase. I did not resolve this.

---

## 7. What I did not do

- **Did not change the ranking function.** `score_provision`, `_strength` and
  the tie-breaks are untouched. Rank movements come only from marker and
  determinacy changes feeding the existing scoring.
- **Did not ship an `om inte` fix.** See Decision 1.
- **Did not fix the other wildcard markers.** Part C is inventory only.
  `får inte` has the same defect at 1.9% of hits and `undantag` does not have it
  at all; both are left alone so that one change stays attributable.
- **Did not edit any frozen artifact.** The gold set, the marker fixture and the
  v1 counts are as committed. The fixture failure in Decision 2 is left failing.
- **Did not touch the parser.** `sfs_parser.py` governs the frozen v1 counts.
- **Did not touch the Databricks pipeline** beyond the one-character notebook
  marker in A1, which you asked for.
- **Did not touch `simulacria/`, contracts, the corpus, or `direction.py`,** and
  made no LLM call of any kind.
- **Did not reformat the frozen tree.** A2 excluded it from `ruff format`
  instead; linting still covers it.
- **Did not add a dependency.** Nothing new was installed this run.
