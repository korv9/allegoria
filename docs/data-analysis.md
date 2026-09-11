# Concrete data and SQL workflow

## Decision

Keep Python + DuckDB for the local experiment. Medallion is the progression from raw
records through verified data to analytical results, not a requirement to duplicate
Python folders or deploy Databricks. dbt can be considered if shared SQL models become
hard to maintain; it adds no necessary capability to this small projection today.

References: [Databricks medallion pattern](https://docs.databricks.com/gcp/en/lakehouse/medallion),
[DuckDB persistent connections](https://duckdb.org/docs/current/connect/overview).

## Ownership and lifecycle

| Evidence/layer | Location | Handling |
| --- | --- | --- |
| Original legal responses | `data/source/sfs/` | Tracked XML + hashes; never overwrite during an experiment |
| Source envelopes (Bronze) | `data/bronze/sfs/` | Tracked full JSON including original XML; parser input |
| Experiment specification | `corpus/`, `prompts/`, `predictions/` | Version in git; annotation drafts are explicitly marked |
| Raw model evidence | `data/local/runs/<run_id>/raw/`, `calls.jsonl`, `manifest.json` | Preserve and back up the whole run directory |
| Verified records (Silver) | `sources.jsonl`, `generations.jsonl`, `readings.jsonl` inside each run | Immutable completed evidence; readers validate output hashes against raw responses |
| SQL projection | `data/local/allegoria.duckdb` | Rebuild with `scripts/build_database.py`; do not hand-edit |
| Analysis (Gold) | `research.slot_comparisons` view, notebooks | Derived observations; no implicit direction or human validation |

Do not treat all of `data/local/` as disposable. Back up the runs before removing local
outputs. A second model call creates new evidence; it does not restore the first call.
Keep failed runs: their status and API receipts explain missing results.
No credentials belong in data artifacts or portfolio exports.

## Implemented database

`selection.provisions`, `selection.candidates`, `selection.marker_hits` and
`selection.markers` are snapshots of the existing Parquet tables for the selected pool.
Join a passage to a provision using `passage_id = provision_id`; also check the
source hash when comparing different corpus versions.

| Research table | One row per | Key |
| --- | --- | --- |
| `runs` | Run manifest | `run_id` |
| `texts` | Source or generated text within a run | `(run_id, text_id)` |
| `source_slots` | Draft slot anchored in an original text | `(run_id, text_id, slot_id)` |
| `readings` | Model reading of one text | `(run_id, call_id)` |
| `slot_observations` | Slot in one reading | `(run_id, call_id, slot_id)` |
| `call_events` | Recorded API lifecycle event | `(run_id, event_index)` |

Text rows retain content and SHA-256; source rows also carry the legal source hash
and URL. Child rows point to `parent_text_id` in the same run and retain style,
prompt variant and API call ID. Model versions and response IDs live on readings;
full requests, generation model and raw-response paths are available in call receipts.
The manifest contains code/prompt hashes, parameters, costs and run status.
Primary and foreign keys reject duplicate records and orphan readings.

Generation zero IDs are deterministically assigned `source:<passage_id>` in the SQL
projection because the initial pilot does not persist its temporary source text IDs.
The importer currently accepts only the actual Gen 0 ? Gen 1 file contract. It rejects
later generations until the writer records explicit parent IDs; it never guesses a
parent from a text hash. The table shape can accommodate that later extension.

`slot_comparisons` aligns source slots with parent and child readings. Missing readings
remain SQL NULL. Multiple reader calls remain separate evidence and can multiply joined
comparisons; filter reader IDs when comparing repeated readings. An absent reader slot
is a model observation, not proof of semantic loss. Direction is not computed.

## Queries

Build, then query the persistent file read-only:

```powershell
python scripts/build_database.py
python scripts/query.py --database data/local/allegoria.duckdb -c "SELECT * FROM research.runs"
```

Inspect original text beside each generation:

```sql
SELECT child.run_id, child.passage_id, child.generation, child.style, child.variant,
       parent.text AS original, child.text AS generated
FROM research.texts child
JOIN research.texts parent
  ON parent.run_id = child.run_id AND parent.text_id = child.parent_text_id;
```

Inspect changes, including unread slots, without declaring loosening:

```sql
SELECT run_id, passage_id, style, variant, slot_id, source_quote,
       parent_status, child_status, child_quote, run_status
FROM research.slot_comparisons
WHERE parent_status IS DISTINCT FROM child_status
   OR parent_status IS NULL OR child_status IS NULL;
```

Count observations with the available denominator visible:

```sql
SELECT style, parent_status, child_status, count(*) AS slot_comparisons
FROM research.slot_comparisons
WHERE run_status = 'completed'
GROUP BY ALL ORDER BY ALL;
```

With no real model runs, the research tables are correctly empty. Selection tables
still contain real law data. The build performs no model calls and creates no sample
results. A failed rebuild rolls back changes to the previous database tables.

## Portfolio later

Choose explicit run IDs and export reviewed query results to JSON or Parquet. Include
run status, model versions, source URLs, denominators and human-review status.
A static page should read this export, not run model calls or expose the database for
arbitrary public writes. The current task prepares the queryable evidence; it does not
publish a demo or claim that a generation experiment has completed.
