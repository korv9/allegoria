# LAS data pipeline

This document describes how the initial LAS corpus is handled at every data layer. Durable choices and their rationale are recorded in `DATA_DECISIONS.md`.

## Build command

From the repository root:

```powershell
python -m backend.lakehouse.pipeline
```

The build is deterministic and performs no network requests. It reads the committed source snapshot and replaces the derived Bronze, Silver, Gold, and quality artifacts with reproducible output.

## DataFrame flow

The implementation deliberately follows a Databricks-style mental model:

```python
bronze_df = build_bronze_df()
silver_df = build_silver_df(bronze_df)
gold_df = build_gold_df(bronze_df, silver_df)
quality_df = build_quality_df(silver_df, gold_df)
```

Inside each transformation, every material operation is assigned to a named DataFrame. Relationships use the same visible sequence as SQL or PySpark:

```python
joined_df = left_df.merge(
    right_df,
    on="document_id",
    how="left",
    validate="many_to_one",
    indicator="metadata_match",
)
if joined_df["metadata_match"].ne("both").any():
    raise ValueError("Rows are missing required metadata")

joined_df["new_column"] = ...
joined_df = joined_df.astype(
    {
        "identifier": "string",
        "numeric_column": "int64",
    }
)
output_df = joined_df.loc[:, OUTPUT_COLUMNS]
```

`validate` declares the expected join cardinality. `indicator` verifies that every left-side row found a required match. This corresponds to a SQL `LEFT JOIN` followed by `WITH COLUMN`, `CAST`, and `SELECT` operations in PySpark.

Source parsing is kept outside the tabular Silver transformation. `backend.ingestion.las_html.parse_las_html()` converts Riksdagen HTML into `provisions_df`; `build_silver_df()` then performs only visible DataFrame operations.

### Relational flow

| Output | Left DataFrame | Operation | Right DataFrame | Cardinality |
| --- | --- | --- | --- | --- |
| Bronze | `source_df` | left merge on `document_id` | `provenance_df` | one-to-one |
| Silver | `provisions_df` | left merge on `document_id` | `document_metadata_df` | many-to-one |
| Gold | `chunk_parts_df` | left merge on `provision_id` | `provision_metadata_df` | many-to-one |
| Quality | `silver_profile_df` | left merge on `document_id, kind` | `gold_profile_df` | one-to-one |

## SOURCE

**Input:** `data/source/las/sfs-1982-80.xml`

The file is the exact response retrieved from Riksdagen's open-data endpoint. `backend.ingestion.load_las()` verifies its pinned SHA-256 before parsing XML. Any mismatch stops the pipeline.

`.gitattributes` marks raw XML as non-text so Git cannot normalize its line endings on different operating systems.

`data/source/las/provenance.json` records the document identity, URLs, retrieval time, source publication time, local filename, and hash.

No source content is changed at this layer.

## Bronze

**Output:** `data/bronze/las/sfs-1982-80.json`

Bronze converts the XML envelope into one inspectable document record. It retains:

- document identity and version
- issue, publication, and retrieval timestamps
- source URLs and source hash
- exact XML-decoded plain text
- exact XML-decoded HTML

Bronze does not split, clean, or chunk legal text. The source XML remains the byte-level authority.

### Bronze columns

| Column | Type | Transformation |
| --- | --- | --- |
| `document_id` | `string` | Copied from XML `dok_id` |
| `title` | `string` | Copied from XML `titel` |
| `version` | `string` | Copied from XML `subtitel` |
| `issued_at` | `string` | Copied without timezone assumptions |
| `published_at` | `string` | Copied without timezone assumptions |
| `retrieved_at` | `string` | Added from provenance |
| `source_page_url` | `string` | Added from provenance |
| `source_data_url` | `string` | Added from provenance |
| `source_sha256` | `string` | Added from verified source bytes |
| `text` | `string` | Exact XML-decoded source text |
| `html` | `string` | Exact XML-decoded source HTML |

## Silver

**Output:** `data/silver/las/provisions.jsonl`

Silver creates one JSON record per legal provision:

- 70 numbered paragraph provisions from `a.paragraf` anchors
- 22 transitional provisions from unique SFS markers under `#overgang`

Silver collapses layout-driven horizontal whitespace while preserving logical blank lines and list breaks. Every provision includes a deterministic ID, its source anchor, position, heading, label, source URL, and canonical source hash.

The source plain text is not parsed with line-start regular expressions because its presentation wrapping can place cross-references such as `39 §§` at the beginning of a line.

### Silver columns

| Column | Type | Transformation |
| --- | --- | --- |
| `provision_id` | `string` | `document_id + ':' + provision_suffix` |
| `document_id` | `string` | Copied from Bronze |
| `kind` | `string` | `paragraph` or `transitional_provision` |
| `source_anchor` | `string` | Parsed from source HTML |
| `label` | `string` | Paragraph label or transition SFS number |
| `heading` | `string` | Parsed from the nearest source heading |
| `order` | `int64` | Assigned in source order |
| `text` | `string` | Whitespace-normalized provision text |
| `subsection_anchors` | `object` containing list | Parsed source anchors |
| `amendment_notes` | `object` containing list | Parsed italic amendment annotations |
| `source_url` | `string` | Bronze page URL plus source anchor |
| `source_sha256` | `string` | Copied from Bronze |

## Gold

**Output:** `data/gold/las/chunks.jsonl`

Gold prepares provisions for later retrieval. A provision remains one chunk when its retrieval text is at most 2,000 characters. Longer provisions are divided only at Silver blank-line boundaries and never inside a sentence or list item.

Each record separates:

- `content`: the Silver-derived legal text segment
- `retrieval_text`: title, heading, provision label, and content

Gold IDs extend their Silver provision ID with an ordered chunk suffix. Joining a provision's ordered Gold `content` fields with blank lines reconstructs its Silver text exactly.

### Gold columns

| Column | Type | Transformation |
| --- | --- | --- |
| `chunk_id` | `string` | `provision_id + ':chunk-' + zero-padded part` |
| `document_id` | `string` | Copied from Silver |
| `provision_id` | `string` | Copied from Silver |
| `kind` | `string` | Copied from Silver |
| `source_anchor` | `string` | Copied from Silver |
| `label` | `string` | Copied from Silver |
| `heading` | `string` | Copied from Silver |
| `part` | `int64` | Chunk order within the provision |
| `part_count` | `int64` | Number of chunks for the provision |
| `content` | `string` | Silver text segment |
| `content_char_count` | `int64` | `len(content)` |
| `retrieval_text` | `string` | Title, heading, label, and content |
| `retrieval_char_count` | `int64` | `len(retrieval_text)` |
| `source_url` | `string` | Copied from Silver |
| `source_sha256` | `string` | Copied from Silver |

## Data Quality

**Output:** `data/quality/las/summary.jsonl`

The pipeline validates critical invariants before writing any derived artifact. It fails if IDs are missing or duplicated, legal text is empty, source hashes differ, Gold omits a Silver provision, a retrieval chunk is oversized, or Gold content cannot reconstruct Silver text.

After validation, the quality profile remains deliberately simple and inspectable. Silver and Gold are independently aggregated by `document_id` and `kind`, then left-joined:

```python
silver_profile_df = silver_df.groupby(
    ["document_id", "kind"], as_index=False
).agg(
    provision_count=("provision_id", "nunique"),
    min_text_chars=("text_char_count", "min"),
    max_text_chars=("text_char_count", "max"),
)

quality_df = silver_profile_df.merge(
    gold_profile_df,
    on=["document_id", "kind"],
    how="left",
    validate="one_to_one",
)
```

This report shows provision counts, chunk counts, and observed text-size ranges. The fail-fast rules enforce Data Quality; the report describes the resulting data. Neither is the later Meaning Quality evaluation of AI outputs.

## Execution platform

The MVP runs with local pandas and committed JSON/JSONL artifacts. Snowflake is excluded from the architecture. If a platform is introduced later, the target is Databricks with PySpark.

The local code therefore uses a narrow set of operations with direct PySpark equivalents:

| pandas now | PySpark on Databricks later | SQL concept |
| --- | --- | --- |
| `df.merge(..., how="left")` | `df.join(..., how="left")` | `LEFT JOIN` |
| `df["column"] = ...` | `df.withColumn("column", ...)` | derived column |
| `df.astype({...})` | `df.select(col(...).cast(...))` | `CAST` |
| `df.loc[:, COLUMNS]` | `df.select(COLUMNS)` | `SELECT` |
| `df.groupby(...).agg(...)` | `df.groupBy(...).agg(...)` | `GROUP BY` |

No compatibility wrapper is added. A future Databricks migration should translate the small transformation functions directly rather than hiding both engines behind a generic abstraction.

## Type policy

There are currently no implicit numeric casts:

- ordering and count fields are explicitly `int64`
- identifiers and text are explicitly pandas `string`
- list-valued columns remain `object`
- source timestamps remain strings until their timezone semantics are confirmed

The project does not cast dates merely because they look like dates. A future datetime conversion must define timezone handling and be recorded in `DATA_DECISIONS.md`.

## Verification

```powershell
python -m unittest discover -s tests -v
```

The tests verify:

- canonical source integrity
- Bronze metadata and content preservation
- extraction of all source paragraph anchors
- explicit handling of transitional provisions
- stable and unique lineage IDs
- Gold size limits and complete Silver reconstruction
- SQL-like join cardinalities and required join matches
- fail-fast Data Quality rules and grouped profile totals
- byte-for-byte reproducibility of committed derived artifacts
