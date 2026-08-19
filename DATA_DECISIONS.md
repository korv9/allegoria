# Data Decisions

This file is the canonical log for decisions that affect how Allegoria acquires, preserves, transforms, stores, or retrieves data.

Each decision is append-only in meaning. If a decision changes, add a new entry that explicitly supersedes the old one.

## DD001 — Riksdagen XML is the canonical source snapshot

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Preserve the exact byte response from `https://data.riksdagen.se/dokument/sfs-1982-80` as the canonical local LAS source.
- **Rationale:** The source must remain independently auditable and must not be altered by parsing or formatting.
- **Consequences:** The XML file is never edited in place. Its SHA-256 is verified before any transformation runs. A future retrieval creates a separately identifiable snapshot rather than silently replacing this version.

## DD002 — Pin the initial corpus to one LAS version

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** The initial corpus contains only `sfs-1982-80`, version `t.o.m. SFS 2022:836`, retrieved on 2026-08-19.
- **Rationale:** A single bounded corpus makes lineage, transformation behavior, and evaluation failures understandable.
- **Consequences:** MBL, case law, and later LAS snapshots remain out of scope until the first vertical slice works.

## DD003 — Keep SOURCE separate from derived layers

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Store the byte-exact response under `data/source/`. Bronze, Silver, and Gold are reproducible derived artifacts stored in separate directories.
- **Rationale:** SOURCE proves what was retrieved; derived layers prove what the pipeline did to it.
- **Consequences:** Derived artifacts may normalize or restructure content only through documented code. Every record carries the canonical source hash.

## DD004 — Store Bronze as one inspectable JSON document

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Bronze contains one UTF-8 JSON document with source metadata, provenance, exact XML-decoded text, and exact XML-decoded HTML.
- **Rationale:** The corpus currently contains one small document. JSON is transparent and introduces no storage dependency.
- **Consequences:** Bronze preserves document-level content but is not byte-identical to the XML transport. The original XML remains the byte-level authority.

## DD005 — Derive paragraph boundaries from source HTML anchors

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Silver paragraph boundaries use Riksdagen's `a.paragraf` anchors and nearby `h4` headings from the embedded HTML.
- **Rationale:** Plain text contains presentation line wraps that make line-based regular expressions ambiguous. The HTML exposes explicit source structure.
- **Consequences:** BeautifulSoup is the only added parser dependency. Paragraph IDs retain source anchor names such as `P7` and `P2a`.

## DD006 — Normalize presentation whitespace only in Silver

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Collapse repeated horizontal whitespace and source presentation line wraps when producing Silver paragraph text. Preserve logical paragraph breaks and list line breaks.
- **Rationale:** Riksdagen's text contains layout-driven spacing that harms retrieval but carries no legal meaning.
- **Consequences:** Silver is not a verbatim byte representation. Each record links back to its source anchor and canonical source hash for verification.

## DD007 — Use stable lineage identifiers at every derived layer

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Silver IDs use `<document_id>:<source_anchor>`. Gold IDs will extend the Silver ID rather than generate opaque identifiers.
- **Rationale:** Meaning Quality requires direct traceability from generated output to exact legal source units.
- **Consequences:** IDs remain readable and deterministic across reproducible pipeline runs.

## DD008 — Commit the first derived artifacts

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Commit the small Bronze, Silver, and Gold outputs for the initial LAS corpus.
- **Rationale:** Reviewers can inspect the data model and lineage without first configuring or running the project.
- **Consequences:** Generated artifacts must be deterministic. Tests compare regenerated output with the committed files.

## DD009 — Model transitional provisions as a separate Silver unit

- **Date:** 2026-08-19
- **Status:** Superseded by DD010
- **Decision:** Silver contains 70 paragraph provisions plus one transitional-provisions unit anchored as `overgang`.
- **Rationale:** Riksdagen places transitional provisions after `43 §` under an `h3` heading rather than `a.paragraf` elements. Internal anchors in that block reuse `P43S...` names and are not unique source identifiers.
- **Consequences:** The Silver contract uses the general term `provision`, with `kind` set to either `paragraph` or `transitional_provisions`. Transitional provisions retain the stable page anchor `overgang` but do not expose the duplicated internal anchors as lineage IDs.

## DD010 — Split transitional provisions by explicit SFS marker

- **Date:** 2026-08-19
- **Status:** Active; supersedes DD009
- **Decision:** Create one Silver provision for each of the 22 unique transition markers formatted as `YYYY:number` under the `overgang` heading.
- **Rationale:** Each marker identifies the transition rules attached to a specific amending SFS. Keeping all 22 in one record would mix distinct legal contexts and create an oversized retrieval unit.
- **Consequences:** Transition IDs use `<document_id>:overgang:<year>-<number>`. They all link to the official `#overgang` page anchor because Riksdagen does not provide unique anchors for individual transition markers.

## DD011 — Split Gold only at observed logical block boundaries

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Keep a Silver provision in one Gold chunk when the complete retrieval text is at most 2,000 characters. Split longer provisions greedily only at preserved blank-line boundaries.
- **Rationale:** The 92 Silver provisions have a median length of 435 characters. Only four exceed 2,000 characters, and their largest indivisible logical block is 758 characters. A fixed token window or arbitrary character cut would destroy source structure without benefiting this corpus.
- **Consequences:** No sentence or list item is cut. The pipeline fails if a future indivisible block cannot fit inside the limit, forcing an explicit new decision rather than a silent fallback.

## DD012 — Keep source content separate from retrieval context

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Each Gold record stores both `content` and `retrieval_text`. `content` is the normalized Silver segment; `retrieval_text` prefixes it with the source title, heading, and provision label.
- **Rationale:** Retrieval needs enough context to interpret short provisions, while lineage checks need to distinguish source-derived content from context added by the pipeline.
- **Consequences:** Silver text can be reconstructed exactly by joining a provision's ordered Gold `content` segments with blank lines. Added context is explicit and never presented as part of the provision body.

## DD013 — Disable Git text normalization for raw XML sources

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Mark `data/source/**/*.xml` as `-text` in `.gitattributes` while enforcing LF for derived JSON, JSONL, Markdown, Python, and TOML files.
- **Rationale:** The first commit stored a line-ending-normalized 144,209-byte XML blob even though the 146,007-byte Windows working copy still matched the HTTP response. A checkout on another operating system would therefore not reproduce the pinned source bytes.
- **Consequences:** The next commit must include the canonical XML again. Git will then store and restore the exact 146,007 bytes on every platform, preserving the documented SHA-256.

## DD014 — Express lakehouse transformations as pandas DataFrames

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Bronze, Silver, and Gold transformation functions accept and return pandas DataFrames. Each layer uses named intermediate DataFrames followed by explicit `assign`, `astype`, and column selection operations.
- **Rationale:** The project owner works primarily with Databricks and finds DataFrame lineage easier to review than transformations hidden inside dataclass construction.
- **Consequences:** The pipeline reads as `source_df → bronze_df → silver_source_df → silver_df → gold_source_df → gold_df`. Pandas is now a direct dependency. BeautifulSoup remains responsible only for turning the source HTML into Silver source records.

## DD015 — Cast only fields with confirmed semantics

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Cast identifiers, labels, URLs, hashes, and text to pandas `string`. Cast `order`, `part`, `part_count`, `content_char_count`, and `retrieval_char_count` to `int64`. Keep list-valued columns as Python lists with pandas `object` dtype. Keep source timestamps as strings.
- **Rationale:** Integer ordering and counts have unambiguous semantics. Riksdagen's issue, publication, and retrieval values do not all carry equivalent timezone information, so converting them to one datetime dtype would introduce an unsupported assumption.
- **Consequences:** There are no implicit float columns. Temporal parsing is deferred until timezone and analytical requirements are known and documented in a superseding decision.

## DD016 — Keep the MVP on local pandas; defer Snowflake

- **Date:** 2026-08-19
- **Status:** Partially superseded by DD019
- **Decision:** Run the initial LAS pipeline locally with pandas and JSON/JSONL storage. Do not add Snowflake or Snowpark to the MVP.
- **Rationale:** The current corpus has one document, 92 provisions, and 96 retrieval chunks. Snowflake would add account, warehouse, credential, cost, and remote-execution concerns without improving the legal parsing or transformation semantics.
- **Consequences:** The local pandas decision remains active. The former Snowflake deployment option is superseded by DD019, which names Databricks/PySpark as the only prospective platform direction.

## DD017 — Model lineage with explicit left joins

- **Date:** 2026-08-19
- **Status:** Active; refines DD014
- **Decision:** Use named DataFrames and explicit `merge(..., how="left")` operations for real relationships: source to provenance, provisions to document metadata, and chunks to provision metadata.
- **Rationale:** This makes the flow read like SQL and PySpark, exposes which table contributes each column, and avoids hiding lineage metadata inside chained assignments.
- **Consequences:** Every join declares its expected cardinality with pandas `validate`. A duplicate or otherwise invalid relationship fails the pipeline instead of silently multiplying rows.

## DD018 — Aggregate the first Data Quality report by document and provision kind

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Build separate Silver and Gold profiles with `groupby(..., as_index=False).agg(...)`, then left-join them on `document_id` and `kind`.
- **Rationale:** Provision totals, chunk totals, and observed text-size ranges provide a small but useful verification layer and demonstrate SQL-like aggregation on actual project data.
- **Consequences:** The report is stored as `data/quality/las/summary.jsonl`. It measures deterministic pipeline structure only and must not be presented as Meaning Quality.

## DD019 — Use pandas locally and Databricks/PySpark only as a future platform

- **Date:** 2026-08-19
- **Status:** Active; supersedes the future-platform option in DD016
- **Decision:** Snowflake is not part of the project architecture. Run the local pipeline with pandas. If a data platform is introduced later, target Databricks and translate the transformations to PySpark.
- **Rationale:** The owner wants a simple local development loop now and already works with the Databricks DataFrame model. Maintaining two execution engines or a Snowflake deployment would add complexity without helping the current LAS experiment.
- **Consequences:** Code uses named DataFrames and operations with direct SQL/PySpark equivalents. No pandas/PySpark compatibility abstraction is introduced before a real migration exists.

## DD020 — Keep transformations column-explicit and source parsing separate

- **Date:** 2026-08-19
- **Status:** Active; refines DD014 and DD017
- **Decision:** Express joins, derived columns, casts, grouped aggregations, and final selects as separate visible statements. Keep Riksdagen HTML traversal in `backend/ingestion/las_html.py`, outside the Silver table transformation.
- **Rationale:** This makes each column's origin and transformation readable in the same order as SQL or PySpark while preventing source-specific parsing from obscuring the relational flow.
- **Consequences:** Avoid opaque method chains, row-wise DataFrame `apply`, generic transformation frameworks, and placeholder abstractions. Type mappings list every cast column explicitly.

## DD021 — Fail the build when critical Data Quality invariants break

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Before writing derived artifacts, validate required and unique IDs, non-empty legal text, complete Silver-to-Gold coverage, consistent source hashes, retrieval size limits, and exact reconstruction of Silver content from ordered Gold chunks.
- **Rationale:** A profile containing counts and ranges describes data but does not validate it. Legal lineage failures must stop the pipeline rather than appear only as metrics.
- **Consequences:** `validate_las_data()` runs before profile creation and all writes. Left joins also use merge indicators so unmatched lineage rows fail explicitly.
