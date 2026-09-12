# %% [markdown]
# # Pipeline walkthrough
#
# What the selection pipeline does to a provision, end to end, on committed data.
# No network. Deterministic. Run top to bottom.
#
# **Every cell calls library code.** No cell computes a marker hit, a determinacy
# rung or a score of its own. If something here needed logic that was not
# importable, that was a finding about `simulacria/` and the library was changed
# — not the cell. A second implementation in a notebook is worse than no
# notebook, because the day it disagrees with the real one you will have
# reviewed the wrong system.
#
# Prerequisites: `pip install -e ".[dev]"`, then
# `python scripts/pipeline/build_silver.py` and `python scripts/pipeline/build_tables.py` for
# whichever pool you select below.

# %%
import time

import pandas as pd
from IPython.display import HTML, display

from simulacria.pipeline.silver import POOLS, bronze_document, build_provisions, check
from simulacria.pipeline.store import TABLE_NAMES, query
from simulacria.selection import highlight
from simulacria.selection.determinacy import classify
from simulacria.selection.inspect import inspect_provision, provenance
from simulacria.selection.markers import ceiling_hits
from simulacria.selection.shortlist import score_breakdown, shortlist

# Change this one line to re-run the whole notebook against the other pool.
POOL = POOLS["v1"]

# Documents and provisions this walkthrough follows. Both exist in v1 and v2.
DOCUMENT_ID = "sfs-2026-1281"
PROVISION_ID = "sfs-2026-1281:K10P10"

pd.set_option("display.max_colwidth", 90)
pd.set_option("display.width", 200)

print(f"pool {POOL.name}  |  bronze {POOL.bronze_dir}  |  tables {POOL.tables_dir}")

# %% [markdown]
# ## 1. Source → Bronze
#
# The provenance chain: where the bytes came from, and what proves they have not
# changed. `provenance()` recomputes the SHA-256 from the file on disk rather
# than reading back the one stored beside it — a digest that is only ever read
# proves nothing.
#
# `roundtrips_to_bronze` is the stronger check: the `raw_xml` field in the bronze
# JSON, re-encoded to UTF-8, must be byte-identical to the source file. That is
# what makes the JSON record an honest carrier of the original response.

# %%
chain = provenance(DOCUMENT_ID, POOL)
display(
    pd.DataFrame(
        [(k, v) for k, v in chain.items() if k != "bronze_keys"], columns=["field", "value"]
    )
)
print("SHA-256 matches the committed bytes:", chain["sha256_matches"])
print("bronze raw_xml round-trips to those bytes:", chain["roundtrips_to_bronze"])

# %%
# The raw XML as committed, and the bronze record built from it.
bronze = bronze_document(DOCUMENT_ID, POOL)
print(str(bronze["raw_xml"])[:600], "\n...")
print("\nbronze fields:", ", ".join(chain["bronze_keys"]))
print(f"\nhtml {len(str(bronze['html'])):,} chars | text {len(str(bronze['text'])):,} chars")

# %% [markdown]
# ## 2. Bronze → provisions
#
# `build_provisions` parses every committed bronze document. **This is the
# slowest cell in the notebook** — it re-parses every document's HTML rather than
# reading the built JSONL, so that the contract below is checked against a fresh
# parse. It times itself; v2 takes substantially longer than v1.
#
# The count is a contract, not a log line. `check()` returns the list of ways the
# build violates its pool's contract: expected document and provision counts,
# uniqueness of every derived `provision_id`, and a `source_sha256` on every row.
# An empty list is a pass. v2 has no expected counts, so only the structural
# checks apply there.

# %%
started = time.perf_counter()
provisions, unparsable = build_provisions(POOL.bronze_dir, strict=POOL.strict)
elapsed = time.perf_counter() - started
problems = check(provisions, POOL)

documents = len({str(p["document_id"]) for p in provisions})
print(f"parsed in {elapsed:.1f}s")
print(f"{documents} documents -> {len(provisions):,} provisions")
print(f"expected: {POOL.expected_documents} documents, {POOL.expected_provisions} provisions")
print(f"unparsable, skipped: {len(unparsable)}")
print()
print("CONTRACT: PASS" if not problems else "CONTRACT: FAIL\n  " + "\n  ".join(problems))

# %%
# One document's provisions.
document_rows = pd.DataFrame(
    [
        {
            "provision_id": p["provision_id"],
            "kind": p["kind"],
            "chapter": p["chapter"],
            "label": p["label"],
            "chars": len(str(p["text"])),
        }
        for p in provisions
        if p["document_id"] == DOCUMENT_ID
    ]
)
print(f"{DOCUMENT_ID}: {len(document_rows)} provisions")
display(document_rows.head(15))

# %%
# One provision in full.
chosen = next(p for p in provisions if p["provision_id"] == PROVISION_ID)
print(f"{chosen['provision_id']}  —  {chosen['document_title']}")
print(f"{chosen['chapter']} / {chosen['heading']} / {chosen['label']}")
print(f"{chosen['source_url']}\n")
print(chosen["text"])

# %% [markdown]
# ## 3. Markers, inline
#
# The cell that earns the notebook. Every marker hit shown **where it matched**,
# coloured by category. Hover any highlight for the full list of markers covering
# it — overlaps are real and are kept, because the scoring counts them.
#
# What to look for: whether a marker fired on the words you would have pointed
# at. A marker list tells you `om inte` fired; it cannot tell you that the match
# ran across a clause boundary and left the conditional it claimed to mark. That
# defect was invisible for two sessions and obvious the moment spans were shown
# in place.

# %%
display(HTML(highlight.legend_html()))
display(HTML(highlight.marker_html(chosen["text"])))

# %%
# The same hits as a table, with offsets.
display(pd.DataFrame(highlight.marker_spans(chosen["text"])))

# %% [markdown]
# ## 4. Determinacy
#
# `DIRECTION.md` grades **the qualifier** on the ladder, not the provision. The
# previous specimen sheet got this wrong: it reported provisions as `specific`
# because a deadline sat in the duty or the exception, while the qualifier itself
# was untestable.
#
# Both figures are shown. `provision_determinacy` still drives the ranking score;
# `qualifier_determinacy` is the one to select specimens on. Where they disagree,
# the disagreement is the interesting part.
#
# A vague qualifier has one rung left to fall (`vague → absent`); a specific one
# has two (`specific → vague → absent`). The founding observation was a specific
# qualifier, and the intermediate step is what made it worth studying.

# %%
detail = inspect_provision(PROVISION_ID, POOL, provisions=provisions)
print(f"provision-level : {detail['provision_determinacy']}")
print(f"qualifier-level : {detail['qualifier_determinacy']}")
print(
    "\nagree"
    if detail["provision_determinacy"]["state"] == detail["qualifier_determinacy"]["state"]
    else "\nDISAGREE — the checkable bound is not in the qualifier"
)

# %%
# Which spans were graded, and what each got. `classify` is the same function the
# ladder uses, applied here to one span at a time so the verdict is traceable.
display(
    pd.DataFrame(
        [
            {"marker": label, "start": start, "end": end, "rung": classify(span), "span": span}
            for label, span, start, end in detail["qualifier_spans"]
        ]
    )
)

# %% [markdown]
# ## 5. Scoring and ranking
#
# The score is deliberately crude and orders a reading list. It is **not** a
# measurement: a high rank means "read this first", never "more degraded".
#
# Per category it takes the strongest marker plus a capped bonus for
# corroborating ones — summing instead would float a sprawling provision with
# eight weak markers above a clean three-part one. Then bonuses for a checkable
# qualifier and for twinnable length. Ties break toward shorter text.

# %%
breakdown = score_breakdown(chosen["text"])
display(pd.DataFrame([breakdown["components"]]).T.rename(columns={0: "points"}))
print(f"total {breakdown['total']}  |  rank {detail['rank']}  |  {breakdown['char_count']} chars")
print(f"length fits the twinnable band: {breakdown['length_fit']}")
print("\nstrongest marker per category:")
for category, fired in breakdown["category_hits"].items():
    best = max(fired, key=lambda hit: hit[1])
    print(f"  {category:<10} {best[0]:<22} weight {best[1]}   (of {len(fired)} fired)")

# %%
candidates = shortlist(provisions)
top = pd.DataFrame(
    [
        {
            "rank": i,
            "provision_id": c["provision_id"],
            "score": c["score"],
            "chars": c["char_count"],
            "prov_det": c["determinacy"],
            "qual_det": c["qualifier_determinacy"],
            "exception": ", ".join(c["exception_markers"][:2]),
            "title": str(c["document_title"])[:44],
        }
        for i, c in enumerate(candidates[:15], start=1)
    ]
)
print(f"{len(candidates):,} candidates from {len(provisions):,} provisions")
display(top)

# %% [markdown]
# ## 6. Drill-down
#
# **The cell to use.** Set `PROVISION_ID` at the top of the notebook, or override
# it here, and re-run. One library call returns everything the pipeline knows.

# %%
target = PROVISION_ID  # <- change me
info = inspect_provision(target, POOL, provisions=provisions)

print(f"{target}  |  pool {info['pool']}  |  candidate: {info['is_candidate']}")
print(f"rank {info['rank']}  score {info['score']}  |  tables {info['tables']}")
print(f"provision determinacy : {info['provision_determinacy']['state']}")
print(f"qualifier determinacy : {info['qualifier_determinacy']['state']}")
if info["ceiling_flags"]:
    print("\nceiling? flags (dock + a bound, UNRESOLVED — hand annotation decides):")
    for window in info["ceiling_flags"]:
        print(f"  {window[:88]}")
print()
display(HTML(highlight.marker_html(info["text"])))
display(pd.DataFrame(info["marker_spans"]))
if info["score_breakdown"]:
    display(pd.DataFrame([info["score_breakdown"]["components"]]).T.rename(columns={0: "points"}))

# %% [markdown]
# ## 7. Known failure modes
#
# A notebook that shows only the happy path is a demo. These are the audited
# defects, displayed so they stay visible rather than living in a review file.

# %% [markdown]
# ### 7a. `sfs-1982-673:P23` — a false positive, pinned on purpose
#
# `förbjuden` fires on *förbud* in a penalty provision, and the "ett år" that
# makes it read `specific` is a **prison term**, not a deadline. It is pinned in
# `tests/fixtures/must_surface.yaml` so the marker pair stays covered — the
# fixture protects marker coverage, not specimen quality.

# %%
fp = inspect_provision("sfs-1982-673:P23", POOL, provisions=provisions)
display(HTML(highlight.marker_html(fp["text"])))
print(f"provision determinacy: {fp['provision_determinacy']}")
print("^ 'ett år' here is a sentence length, read as a checkable qualifier")

# %% [markdown]
# ### 7b. `sfs-2026-1283:K5P1` — the number-word gap, now closed
#
# Its determinacy read `unmarked` despite a forty-year review period, because the
# number words stopped at "trettio". The list now runs to "hundra". The fixture
# pinned this provision *to record the gap*, so closing the gap is exactly what
# makes `test_fixture_provisions_hit_their_markers` fail — the one deliberately
# red test in the suite, awaiting a human decision.

# %%
gap = inspect_provision("sfs-2026-1283:K5P1", POOL, provisions=provisions)
print(f"determinacy now: {gap['provision_determinacy']}")
print("fixture pins:    unmarked  <- fails on purpose; do not edit the fixture")
display(HTML(highlight.marker_html(gap["text"])))

# %% [markdown]
# ### 7c. `sfs-2008-567:K1P4` — the corpus's only `såvida inte`
#
# A definitions section, and a poor specimen. Pinned anyway: nothing else in
# 1,952 provisions exercises that marker, so without it a broken `såvida inte`
# would fail silently.

# %%
sole = inspect_provision("sfs-2008-567:K1P4", POOL, provisions=provisions)
sole_hits = [h for h in sole["marker_spans"] if h["marker"] == "såvida inte"]
print(f"`såvida inte` hits in this provision: {len(sole_hits)}")
for hit in sole_hits:
    display(
        HTML(highlight.span_html(sole["text"], int(hit["start"]), int(hit["end"]), "såvida inte"))
    )

# %% [markdown]
# ### 7d. A spurious `om inte`, with the clause boundary marked
#
# The open defect. `\bom\s+(?:\w+\s+){0,3}?inte\b` uses a wildcard gap standing
# in for "same clause", which a regex cannot express — so the gap steps over the
# very tokens that mark the boundary being left. Highlighted in yellow below.
#
# In `sfs-2026-1054:P8` the match is `om att karens inte`: `om att` introduces a
# complement clause, not a condition. The provision's *only* exception evidence
# is this hit, so it is a candidate purely because of the defect. A fix is scored
# in `review/2026-09-11/REVIEW.md` and not shipped.

# %%
spurious = inspect_provision("sfs-2026-1054:P8", POOL, provisions=provisions)
om_inte = [h for h in spurious["marker_spans"] if h["marker"] == "om inte"]
exception_markers = [h["marker"] for h in spurious["marker_spans"] if h["category"] == "exception"]
print(f"exception markers firing: {exception_markers}")
for hit in om_inte:
    print(f"\nspan: {hit['span']!r} at offset {hit['start']}")
    display(
        HTML(highlight.clause_boundary_html(spurious["text"], int(hit["start"]), int(hit["end"])))
    )

# %% [markdown]
# ### 7e. `sfs-2026-578:P19` — the negative control
#
# Carried on the specimen sheet as a control. On a close reading the second
# sentence is a **consequence of breach**, not an exception to the duty. If hand
# annotation ever files it as an exception, the slot schema is too permissive.

# %%
control = inspect_provision("sfs-2026-578:P19", POOL, provisions=provisions)
display(HTML(highlight.marker_html(control["text"])))
print(
    "markers claim an exception:",
    [h["marker"] for h in control["marker_spans"] if h["category"] == "exception"],
)
print("reading says: consequence of breach, not a carve-out")

# %% [markdown]
# ### 7f. `dock` doing two different jobs
#
# `ceiling_hits` flags a `dock` followed by a bound. A bound on a granted power
# is a **ceiling**, not an exception, and removing one *loosens* where removing
# an exception *tightens* — opposite signs from the same marker.
#
# The flag is a screening aid, not a classifier: measured precision on v1 is
# about 53%. Resolution is by hand; see
# `review/2026-09-11/DIRECTION-ceiling-proposal.md`.

# %%
flagged = [
    {"provision_id": c["provision_id"], "window": window[:70]}
    for c in candidates
    for window, bounded in ceiling_hits(str(c["text"]))
    if bounded
]
print(f"{len(flagged)} of {len(candidates):,} candidates carry `dock` + a bound")
display(pd.DataFrame(flagged).head(10))

# %% [markdown]
# ## 8. Tables
#
# The Parquet layer the shortlist is queried through. `marker_hits` covers **all**
# provisions, not only candidates — that is what keeps near-misses and
# never-firing markers answerable.
#
# The queries below are from `docs/queries.md`, run here so the query path is
# exercised rather than described.

# %%
for name in TABLE_NAMES:
    columns, rows = query(POOL.tables_dir, f'select count(*) from "{name}"')
    schema_cols, schema_rows = query(POOL.tables_dir, f'describe "{name}"')
    print(f"\n{name}: {rows[0][0]:,} rows")
    display(pd.DataFrame(schema_rows, columns=schema_cols)[["column_name", "column_type"]].T)

# %%
# docs/queries.md #2 — determinacy across candidates, both figures side by side.
columns, rows = query(
    POOL.tables_dir,
    """
    select determinacy, qualifier_determinacy, count(*) as candidates
    from candidates group by 1, 2 order by candidates desc
    """,
)
display(pd.DataFrame(rows, columns=columns))

# %%
# docs/queries.md #3 — marker frequency, and which markers never fire. The left
# join is the point: a marker that never matches has no rows to count.
columns, rows = query(
    POOL.tables_dir,
    """
    select m.category, m.marker, m.weight,
           count(h.provision_id) as hits,
           count(distinct h.provision_id) as provisions
    from markers m
    left join marker_hits h on h.category = m.category and h.marker = m.marker
    group by 1, 2, 3 order by hits asc
    """,
)
display(pd.DataFrame(rows, columns=columns))

# %%
# docs/queries.md #5 — near-misses: duty and exception, but no qualifier. These
# are not candidates, which is why marker_hits must span every provision.
columns, rows = query(
    POOL.tables_dir,
    """
    with parts as (
      select provision_id,
             count(*) filter (where category = 'duty')      > 0 as has_duty,
             count(*) filter (where category = 'exception') > 0 as has_exception,
             count(*) filter (where category = 'qualifier') > 0 as has_qualifier
      from marker_hits group by provision_id
    )
    select p.provision_id, p.label, p.char_count, p.document_title
    from parts join provisions p using (provision_id)
    where has_duty and has_exception and not has_qualifier
    order by p.char_count limit 10
    """,
)
display(pd.DataFrame(rows, columns=columns))

# %% [markdown]
# ## What this notebook does not show
#
# - **Which part a qualifier attaches to.** It decides the sign of a removal and
#   `DIRECTION.md` assigns it to hand annotation. Nothing here infers it.
# - **Whether a `ceiling?` flag is really a ceiling.** Same reason.
# - **`direction` itself.** That is `simulacria.measurement`, empty until Phase 2,
#   and it may not import anything shown above.
