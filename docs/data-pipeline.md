# Allegoria SFS medallion pipeline

## Source and ingestion

`products/allegoria/sfs_ingestion.py` resolves a 50-law manifest through Riksdagen's document
list, fetches every full SFS response, and validates the entire batch before writing.

```text
Riksdagen document list
        |
        `-- 6 domain seeds + 44 recent laws
                |
                v
data/source/sfs/*.xml       exact response bytes
data/source/sfs/manifest.json
                |
                v
data/bronze/sfs/*.json      full source-shaped payload
```

Source XML is the byte authority. Bronze JSON includes the same XML as lossless UTF-8 in
`raw_xml`, plus decoded source fields. Tests verify that `raw_xml.encode("utf-8")` reconstructs
the source file and that both match the manifest SHA-256.

## Bronze

Notebook: `products/allegoria/bronze/bronze_sfs.py`

Table: `dev_lakehouse.bronze_allegoria.sfs_documents`

One row is one current law snapshot. The notebook reads all `data/bronze/sfs/*.json` files on the
driver, creates one Spark DataFrame, performs an explicit column select, and writes one managed
Delta table.

| Column group | Columns | Handling |
| --- | --- | --- |
| Identity | `document_snapshot_id`, `document_id`, `designation` | retained as strings |
| Source metadata | `title`, `version`, `department`, `source_type`, `source_subtype` | `version` may be null when the API has no subtitle |
| Source time | `issued_at`, `published_at`, `retrieved_at` | retained as source strings |
| Provenance | `source_page_url`, `source_data_url`, `source_raw_file`, `source_sha256` | retained; hash checked locally |
| Full payload | `payload_size_bytes`, `text`, `html`, `raw_xml` | retained without legal rewriting |
| Ingestion | `source_file`, `ingested_at` | added by Bronze |

Bronze fails unless exactly 50 JSON files exist, file names match `document_id`, IDs are unique,
and all snapshot IDs pass declared Data Quality.

## Silver

Notebook: `products/allegoria/silver/silver_sfs.py`

Table: `dev_lakehouse.silver_allegoria.sfs_provisions`

Silver parses all 50 HTML payloads and joins each provision back to its Bronze parent.

| Column group | Columns | Handling |
| --- | --- | --- |
| Identity | `provision_id`, `document_snapshot_id`, `document_id`, `kind`, `order` | deterministic and typed |
| Source hierarchy | `source_anchor`, `source_anchor_occurrence`, `label`, `chapter`, `heading` | read from HTML structure |
| Legal payload | `text`, `subsection_anchors`, `amendment_notes` | presentation whitespace normalized only |
| Document context | `document_title`, `document_version` | left-joined from Bronze |
| Provenance | `source_url`, `source_page_url`, `source_sha256` | retained from Bronze |
| Processing | `bronze_ingested_at`, `silver_transformed_at` | retained/added timestamps |

The source reuses 45 paragraph anchors across the current corpus. These can represent future
effective wording or source-anchor collisions. Silver retains every occurrence and adds an
occurrence suffix to the derived provision ID; it never drops duplicate anchors. A missing
transitional-provisions section is valid, while an existing but unparseable section fails.

The checked-in corpus currently produces 1,952 unique provisions, including 76 transition
blocks. Silver verifies complete document coverage, unique provision IDs, and complete Bronze
lineage before writing.

## Gold

Notebook: `products/allegoria/gold/gold_sfs.py`

Table: `dev_lakehouse.gold_allegoria.sfs_provision_summary`

Gold adds `text_char_count` and groups provisions by document, provision kind, chapter, and
heading. It calculates provision count, order bounds, text-length bounds, average text length,
and refresh time. The checked-in corpus produces 1,001 groups.

Gold reconciles the sum of group counts to the distinct Silver provision count. It does not
chunk, summarize, embed, rank, or alter legal text.

## Notebook output

Every transformation notebook prints one bounded summary, for example:

```text
SILVER | rows 50 laws -> 1952 provisions | changed: ... | output: Delta
```

Optional previews show selected identifiers and metadata, never the full raw legal payload.
