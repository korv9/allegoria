# Allegoria medallion pipeline

## Source and storage flow

```text
Canonical XML (byte-pinned, never transformed in place)
    |
    `-- decoded and recorded in checked-in Bronze JSON
            |
            v
        Bronze managed Delta table
            |
            v
        Silver managed Delta table
            |
            v
        Gold managed Delta table
```

Lakehouse Engine performs Delta reads, Data Quality, and write boundaries. The Bronze workspace
JSON is the one exception: Python reads the single Git-folder file on the driver and immediately
creates a Spark DataFrame. The code between boundaries is explicit PySpark and uses named
DataFrames.

## Bronze

Table: `dev_lakehouse.bronze_allegoria.las_documents`

One row represents the complete LAS snapshot. Text values remain source-shaped; the layer adds
only ingestion metadata.

| Column group | Columns | Handling |
| --- | --- | --- |
| Identity | `document_id`, `title`, `version` | cast to string |
| Source time | `issued_at`, `published_at`, `retrieved_at` | retained as strings; timezone semantics differ |
| Provenance | `source_page_url`, `source_data_url`, `source_sha256` | retained and hash-checked |
| Legal payload | `text`, `html` | retained without legal rewriting |
| Ingestion | `source_file`, `ingested_at` | added by Bronze |

The notebook fails unless the source contains exactly one document and the hash matches the
canonical XML snapshot.

## Silver

Table: `dev_lakehouse.silver_allegoria.las_provisions`

Silver parses the actual Riksdagen HTML structure into 70 paragraph provisions and 22 separately
identified transitional provisions. It uses an explicit left join from parsed provisions to the
Bronze document metadata.

| Column group | Columns | Handling |
| --- | --- | --- |
| Identity | `provision_id`, `document_id`, `kind`, `order` | deterministic ID; integer order |
| Source structure | `source_anchor`, `label`, `heading` | derived from HTML anchors/headings |
| Legal payload | `text`, `subsection_anchors`, `amendment_notes` | normalized presentation whitespace only |
| Document context | `document_title`, `document_version` | left-joined from Bronze |
| Provenance | `source_url`, `source_page_url`, `source_sha256` | left-joined from Bronze |
| Processing | `bronze_ingested_at`, `silver_transformed_at` | retained/added timestamps |

The notebook fails on unmatched lineage, duplicate provision IDs, missing IDs, or any row count
other than the verified 92.

## Gold

Table: `dev_lakehouse.gold_allegoria.provision_summary`

Gold does not chunk legal text. It adds `text_char_count`, groups Silver by document, provision
kind, and heading into 19 summary rows, and calculates:

- `provision_count`
- `first_order` and `last_order`
- `min_text_chars`, `average_text_chars`, and `max_text_chars`
- `refreshed_at`

The source page URL and SHA-256 remain in each group. A reconciliation check verifies that the
sum of Gold `provision_count` equals the distinct Silver provision count.

## Notebook output

Each transformation notebook always prints one compact line:

```text
SILVER | rows 1 document -> 92 provisions | changed: ... | output: Delta
```

When preview is enabled, it also shows a limited selection of columns and at most 3–10 rows.
This is intended to make the change visible without dumping legal text or full schemas.
