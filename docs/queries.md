# Querying the candidate shortlist

The shortlist is Parquet, not a printout. Build the tables once, then ask
questions of them:

```powershell
python scripts/pipeline/build_silver.py     # data/local/provisions.jsonl
python scripts/pipeline/build_tables.py     # data/local/tables/*.parquet
python scripts/report/query.py -c "select count(*) from candidates"
```

`scripts/report/query.py` registers four views over `data/local/tables/` and runs the
SQL you hand it, on `-c` or on stdin. There is no schema layer to learn — run
`describe provisions` to see the columns.

| Table | Grain | Rows |
| --- | --- | ---: |
| `provisions` | one row per parsed provision | 1,952 |
| `candidates` | one row per surfaced candidate, ranked | 460 |
| `marker_hits` | one row per marker occurrence, **across all provisions** | 8,940 |
| `markers` | the marker inventory itself | 27 |

## Pools

Every script takes `--pool v1|v2`, defaulting to `v1`.

| Pool | Corpus | Tables |
| --- | --- | --- |
| `v1` | the frozen 50-law snapshot, 1,952 provisions | `data/local/tables/` |
| `v2` | the larger selection pool (see `DD040`) | `data/local/tables_v2/` |

```powershell
python scripts/pipeline/ingest_sfs_pool.py                    # fetch the pool (resumable)
python scripts/pipeline/build_silver.py --pool v2
python scripts/pipeline/build_tables.py --pool v2
python scripts/report/query.py --pool v2 -c "select count(*) from candidates"
```

v1 keeps its hard expected counts and is the regression corpus. v2 has none, and
every query below runs unchanged against either pool.

Two things worth knowing before you write a query:

- `marker_hits` covers every provision, not only candidates. That is deliberate:
  a near-miss is by definition not a candidate, so restricting hits to the
  shortlist would make question 5 below unanswerable.
- `has_duty`, `has_exception` and `has_qualifier` on `candidates` are **always
  true** — a provision only becomes a candidate by hitting all three. They are
  kept for schema clarity. To find provisions that hit some but not all, go to
  `marker_hits`.

---

## 1. Candidate count by document, descending

Where the material actually is.

```sql
select p.document_id, any_value(p.document_title) as title, count(*) as candidates
from candidates c join provisions p using (provision_id)
group by p.document_id
order by candidates desc, p.document_id;
```

Elmarknadslag alone contributes 72 of 460 — it is a long, heavily conditioned
statute. Worth remembering when picking corpus passages: an unstratified pick
from the top of the ranking will over-sample electricity market law.

## 2. Distribution of `determinacy` across candidates

How many candidates carry a qualifier you could actually test.

```sql
select determinacy, count(*) as candidates,
       round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from candidates
group by determinacy
order by candidates desc;
```

`unmarked` 300 (65.2%), `specific` 114 (24.8%), `vague` 46 (10.0%). Only a
quarter of the shortlist has a checkable qualifier, which is the population that
matters for observing qualifier death on the ladder.

## 3. Marker frequency by category, and which markers never fire

The left join is the point — a marker that never matches has no rows in
`marker_hits`, so it can only be named by joining from the inventory.

```sql
select m.category, m.marker, m.weight,
       count(h.provision_id) as hits,
       count(distinct h.provision_id) as provisions
from markers m
left join marker_hits h on h.category = m.category and h.marker = m.marker
group by m.category, m.marker, m.weight
order by hits asc, m.category, m.marker;
```

**No marker is dead** — all 27 fire at least once. The tail is thin though:
`såvida inte` fires exactly once in 1,952 provisions, `måste` four times,
`utan hinder av` six. The head is `om` at 3,423 hits across 1,449 provisions,
which is why it carries weight 1 and cannot lift a candidate on its own.

## 4. Short, checkable candidates by rank

The most workable corpus passages: a testable qualifier in under 300 characters,
short enough to hand-twin without rewriting a page of prose.

```sql
select c.rank, c.provision_id, p.label, c.char_count,
       c.exception_marker, c.qualifier_marker
from candidates c join provisions p using (provision_id)
where c.determinacy = 'specific' and c.char_count < 300
order by c.rank;
```

Ten rows. `sfs-1977-480:P12` at rank 10 and 276 characters is the strongest —
`om inte` carve-out with a `särskilda skäl` qualifier.

## 5. Near-misses: duty + exception, no qualifier

Provisions the shortlist rejects for lacking a condition. Worth eyeballing: some
are genuinely two-part rules, others carry a condition the markers do not know.

```sql
with parts as (
  select provision_id,
         count(*) filter (where category = 'duty')      > 0 as has_duty,
         count(*) filter (where category = 'exception') > 0 as has_exception,
         count(*) filter (where category = 'qualifier') > 0 as has_qualifier
  from marker_hits
  group by provision_id
)
select p.provision_id, p.label, p.char_count, p.document_title
from parts join provisions p using (provision_id)
where has_duty and has_exception and not has_qualifier
order by p.char_count;
```

Reading the shortest ones, these are mostly **genuine two-part rules** — a duty
with a flat carve-out and no condition attached to either part:

> Centralmyndigheten **har rätt att** för sin tillsyn få tillträde till områden,
> lokaler och andra utrymmen, **dock inte bostäder**, där den som står under
> tillsyn bedriver sin verksamhet. — `sfs-2026-966:K3P3`

That is a correct rejection: with no qualifier there is nothing to watch die.
But the list also exposes a real marker gap. `sfs-2026-456:P2` reads "i den
utsträckning som denna lag avviker från utlänningslagen" — a scope condition
that the qualifier set misses, because it knows `i den mån` but not
`i den utsträckning`. Near-misses are where that class of omission surfaces.

## 6. Documents contributing zero candidates

```sql
select p.document_id, any_value(p.document_title) as title, count(*) as provisions
from provisions p
where p.document_id not in (
    select distinct p2.document_id
    from candidates c join provisions p2 using (provision_id)
)
group by p.document_id
order by provisions desc;
```

Six of 50 laws contribute nothing. Five are tiny (1–16 provisions) — narrow
single-purpose acts. The outlier is `sfs-2026-955` (avgift för
områdessamverkan), 22 provisions and not one candidate: its opening chapter is
almost entirely definitional ("I denna lag betyder …"), which produces duties
without carve-outs and so never trips the exception markers.

## 7. Which exception markers actually pay off

Marker frequency says how often a pattern fires; this says whether firing buys
anything. Restricted to markers carrying at least five candidates.

```sql
select c.exception_marker,
       count(*) as candidates,
       count(*) filter (where c.determinacy = 'specific') as specific,
       round(avg(c.score), 1) as avg_score,
       round(avg(c.char_count)) as avg_chars
from candidates c
group by c.exception_marker
having count(*) >= 5
order by specific * 1.0 / count(*) desc;
```

`dock` leads at 46/155 specific. `undantag` is the weakest: 2 of 26 specific and
an average of 881 characters, i.e. it fires mostly inside long delegation
clauses ("regeringen får meddela föreskrifter om undantag") rather than on real
carve-outs.

## 8. Best specimen per document

For spreading a corpus across statutes instead of taking the top N globally.

```sql
select any_value(p.document_title) as title,
       min(c.rank) as best_rank,
       arg_min(c.provision_id, c.rank) as provision_id,
       arg_min(c.determinacy, c.rank) as determinacy
from candidates c join provisions p using (provision_id)
group by p.document_id
order by best_rank;
```

Every one of the top ten documents has a `specific` best candidate, so a
stratified pick costs little in specimen quality.
