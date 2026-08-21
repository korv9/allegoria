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
| Ingestion | `bronze_ingested_at` | added by Bronze |

Bronze fails unless exactly 50 JSON files exist, file names match `document_id`, IDs are unique,
the stored SHA-256 matches `sha2(raw_xml, 256)`, and all snapshot IDs pass declared Data Quality.
The local Workspace path is deliberately not persisted; `source_raw_file` is only the portable
source filename from the checked corpus.

## Silver

Notebook: `products/allegoria/silver/silver_sfs.py`

Table: `dev_lakehouse.silver_allegoria.sfs_provisions`

Silver parses all 50 HTML payloads and joins each provision back to its Bronze parent.

| Column group | Columns | Handling |
| --- | --- | --- |
| Identity | `provision_id`, `document_snapshot_id`, `document_id`, `kind`, `order` | deterministic and typed |
| Source hierarchy | `source_anchor`, `source_anchor_occurrence`, `label`, `chapter`, `heading` | read from HTML structure |
| Legal payload | `text`, `provision_text_sha256`, `subsection_anchors`, `amendment_notes` | presentation whitespace normalized only; normalized provision text hashed separately |
| Document context | `document_title`, `document_version` | left-joined from Bronze |
| Provenance | `source_url`, `source_page_url`, `source_sha256` | retained from Bronze |
| Processing | `bronze_ingested_at`, `silver_transformed_at` | retained/added timestamps |

The source reuses 45 paragraph anchors across the current corpus. These can represent future
effective wording or source-anchor collisions. Silver retains every occurrence and adds an
occurrence suffix to the derived provision ID; it never drops duplicate anchors. A missing
transitional-provisions section is valid, while an existing but unparseable section fails.

`source_sha256` identifies the complete raw source document and is therefore intentionally the
same on all provisions from one snapshot. `provision_text_sha256` identifies one normalized
Silver provision and can later be carried into retrieval results.

The checked-in corpus currently produces 1,952 unique provisions, including 76 transition
blocks. Silver verifies complete document coverage, unique provision IDs, and complete Bronze
lineage before writing.

## Gold

Notebook: `products/allegoria/gold/gold_sfs.py`

Table: `dev_lakehouse.gold_allegoria.sfs_provision_summary`

Gold adds `text_char_count` and groups provisions by source snapshot, document, provision kind,
chapter, and heading. It calculates provision count, order bounds, and text-length statistics.
It also carries document metadata and the Bronze, Silver, and Gold processing timestamps so the
profile can be traced back to the exact snapshot. The checked-in corpus produces 1,001 groups.

Gold reconciles the sum of group counts to the distinct Silver provision count. It does not
chunk, summarize, embed, rank, or alter legal text.

## Gold retrieval chunks

Notebook: `products/allegoria/gold/gold_sfs_retrieval_chunks.py`

Table: `dev_lakehouse.gold_allegoria.sfs_retrieval_chunks`

This independent Gold output converts 1,952 Silver provisions into 1,967 retrieval chunks. It
keeps a complete provision in one chunk when `retrieval_text` is at most 2,000 characters. The
11 longer provisions are split greedily only at the blank-line boundaries preserved in Silver.
An indivisible legal block that cannot fit causes a failure rather than an arbitrary text cut.

| Column group | Columns | Handling |
| --- | --- | --- |
| Chunk identity | `chunk_id`, `provision_id`, `part`, `part_count`, `chunking_strategy` | deterministic and typed |
| Source hierarchy | `document_id`, `kind`, `source_anchor`, `label`, `chapter`, `heading`, `provision_order` | retained from Silver |
| Legal content | `content`, `content_char_count`, `chunk_text_sha256` | source-derived content only |
| Retrieval content | `retrieval_text`, `retrieval_char_count`, `retrieval_byte_count` | hierarchy context plus content |
| Provenance | `document_snapshot_id`, `provision_text_sha256`, `source_url`, `source_sha256` | retained through every chunk |
| Processing | `bronze_ingested_at`, `silver_transformed_at`, `gold_prepared_at` | retained/added timestamps |

Ordered `content` chunks must reconstruct every Silver `text` with the preserved blank-line
separator. The notebook fails on incomplete reconstruction, missing lineage, duplicate IDs,
more than 2,000 retrieval characters, more than 32,764 UTF-8 retrieval bytes, or any row-count
change from the checked corpus contract. Delta Change Data Feed is enabled for a future AI Search
Delta Sync index.

No symbols or semantic interpretations are added during chunking. Those belong after measured
retrieval and source-grounded answer generation.

## Notebook output

Every transformation notebook prints one bounded summary, for example:

```text
SILVER | rows 50 laws -> 1952 provisions | changed: ... | output: Delta
```

Optional previews show selected identifiers and metadata, never the full raw legal payload.
