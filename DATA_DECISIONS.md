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

## DD022 — Establish SQLite FTS5/BM25 as the local lexical retrieval baseline

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Load the committed Gold chunks into an in-memory SQLite FTS5 index and rank full-text matches with BM25. Index only `retrieval_text`; return Gold identity, legal content, source URL, and source hash as unindexed metadata.
- **Rationale:** SQLite FTS5 is available in the existing Python runtime, requires no service or package, exposes retrieval as inspectable SQL, and provides a deterministic keyword baseline before embeddings are introduced.
- **Consequences:** The index is rebuilt from Gold and is never a source of truth. Queries use Unicode prefix tokens combined with `OR`. Empty queries fail and unmatched queries return no rows; there is no retrieval fallback. Semantic and hybrid retrieval remain later candidates to be measured against this baseline.

## DD023 — Evaluate retrieval before answer generation

- **Date:** 2026-08-19
- **Status:** Active
- **Decision:** Store a small, human-labeled LAS retrieval set under `data/evaluation/retrieval/las.jsonl` and measure Hit@k and mean reciprocal rank before adding an LLM answer layer.
- **Rationale:** Retrieval failures must remain visible instead of being hidden by plausible generated prose. The initial set deliberately includes both exact legal terminology and everyday Swedish paraphrases.
- **Consequences:** The first seven-query baseline scores Hit@3 `6/7` and MRR `0.7857`; the missed paraphrase is retained as evidence for later semantic or hybrid retrieval. Evaluation labels are project-authored test data, not legal source content.

## DD024 — Defer embeddings and managed RAG services until Databricks

- **Date:** 2026-08-20
- **Status:** Active; refines DD019, DD022, and DD023
- **Decision:** Finish the local data and retrieval foundation with pandas, Gold JSONL, SQLite FTS5/BM25, and labeled retrieval evaluation. Do not add a local embedding model or a separate external embedding API. After the foundation is verified, introduce embeddings, vector and hybrid retrieval, model inference, and RAG evaluation in Databricks.
- **Rationale:** The local lexical retriever is a deterministic baseline, while Databricks can later provide the managed embedding, search, model-serving, and evaluation capabilities needed by the full RAG experiment. Adding a temporary local or Vertex-based embedding path would create another implementation that the project already intends to replace.
- **Consequences:** Expand the local relevance set before migration and preserve its query and result contracts for comparison. The later Databricks implementation will translate the data pipeline to PySpark/Delta and compare full-text, vector, and hybrid retrieval against the same labeled queries. Application code does not require a separate Vertex AI or direct GCS retrieval pipeline, although Databricks on Google Cloud still uses cloud storage configured beneath Unity Catalog.

## DD025 — Use a versioned context packet as the RAG boundary

- **Date:** 2026-08-20
- **Status:** Active
- **Decision:** Convert ranked retrieval results into context schema `1.0`. The packet contains the exact query, retriever identity, chunk count, and ordered chunks with citation ID, rank, score, legal content, stable lineage IDs, official URL, and canonical source hash.
- **Rationale:** Retrieval engines and score scales can change in Databricks, but answer generation and Meaning Quality need one explicit, testable input contract. Keeping Gold `content` separate prevents retrieval-added headings from being mistaken for legal source text.
- **Consequences:** Context creation fails on empty results, missing lineage, duplicate chunks, or invalid ranks. The prompt-ready representation is derived from the packet without altering legal content. Databricks retrieval must preserve this schema or introduce an explicitly versioned successor.

## DD026 — Expand retrieval evaluation without tuning the lexical baseline

- **Date:** 2026-08-20
- **Status:** Active; refines DD023 and DD024
- **Decision:** Use 30 curated, project-authored positive LAS questions split into `legal_terms` and `natural_language`. Validate that every relevance label resolves to a Gold `provision_id`, and report metrics both overall and by query type.
- **Rationale:** Seven questions cannot characterize retrieval behavior. The expanded set covers major LAS topics and retains natural-language paraphrases that expose BM25's semantic limitations.
- **Consequences:** At top three, the frozen local baseline scores Hit@3 `0.8667` and MRR `0.7667`; legal terms score `1.0000` Hit@3 and natural language `0.7500`. The four misses remain comparison cases for Databricks vector and hybrid retrieval. Questions without a relevant LAS provision are deferred to later answer/abstention evaluation rather than being mixed into positive retrieval metrics.

## DD027 — Make Databricks/PySpark the active data implementation

- **Date:** 2026-08-20
- **Status:** Active; supersedes DD014, DD016, and DD019 for the active pipeline
- **Decision:** Structure the repository as Databricks data products. Use ordinary PySpark for visible transformations and adidas Lakehouse Engine 2.1.1 for reads, declared Data Quality checks, and managed Delta writes.
- **Rationale:** The owner wants the project to match the proven `portfolio-platform` pattern and their normal Databricks working model instead of maintaining a temporary pandas implementation.
- **Consequences:** The local pandas lakehouse and SQLite retrieval code are removed. Lakehouse Engine is pinned because its ACON contract can change between releases. Spark execution is verified in Databricks; local tests cover source parsing and repository contracts.

## DD028 — Store Allegoria layers in product-specific Unity Catalog schemas

- **Date:** 2026-08-20
- **Status:** Superseded by DD035
- **Decision:** Use catalog `dev_lakehouse` by default with managed Delta tables `bronze_allegoria.las_documents`, `silver_allegoria.las_provisions`, and `gold_allegoria.provision_summary`. Retain the checked-in Bronze JSON as the transparent notebook input and the exact XML as the canonical byte authority.
- **Rationale:** Product-specific schemas follow the existing portfolio-platform convention and keep layer plus ownership visible in every three-part table name.
- **Consequences:** Bronze is source-shaped but queryable as Delta after ingestion. Silver and Gold are also Delta. Production uses `prod_lakehouse` through the bundle target rather than changing notebook code.

## DD029 — Keep Gold neutral until retrieval design is approved

- **Date:** 2026-08-20
- **Status:** Active; refined by DD035 for the multi-law implementation
- **Decision:** Gold groups Silver provisions by document, provision kind, and heading and records provision and text-length statistics. Do not create chunks, embeddings, indexes, retrieval evaluation, or RAG contracts in this phase.
- **Rationale:** The owner wants to inspect and understand the completed data layers before choosing how RAG should consume the legal data.
- **Consequences:** The 92 source-traceable Silver provisions remain the likely future retrieval input. Any chunk table requires a new documented decision after Silver and Gold have been run and reviewed.

## DD030 — Do not duplicate LAS into an empty Simulacria pipeline

- **Date:** 2026-08-20
- **Status:** Active
- **Decision:** Place both Allegoria and Simulacria under `products`, but create executable medallion notebooks only for Allegoria now. Simulacria remains a documented product boundary until real generation and reconstruction events exist.
- **Rationale:** Simulacria's source data is future model output, not another copy of LAS. Creating its schemas now would invent contracts before inspecting real source data.
- **Consequences:** No Simulacria Unity Catalog objects or Databricks tasks exist in this phase.

## DD031 — Print one bounded transformation summary per notebook

- **Date:** 2026-08-20
- **Status:** Active
- **Decision:** After every Bronze, Silver, and Gold write, print input rows, output rows, the main transformation, and the output format in one line. Optional previews show only selected columns and a small row limit.
- **Rationale:** The owner needs to see how each dataset changed without receiving full legal payloads or overwhelming Spark output.
- **Consequences:** The short summary always runs. Set `ALLEGORIA_PREVIEW=false` to hide the additional bounded `.show()` output.

## DD032 — Make each Databricks notebook dependency-self-contained

- **Date:** 2026-08-20
- **Status:** Active
- **Decision:** Treat manual notebook execution as the primary development workflow. Bronze, Silver, and Gold install their own pinned Python dependencies with `%pip` and restart Python before imports. `databricks.yml` is optional automation, not a requirement for running the data layers.
- **Rationale:** Job-level libraries are unavailable when a notebook is opened and run directly, which caused `ModuleNotFoundError: No module named 'lakehouse_engine'`. The current workspace also accepts only serverless compute, while the existing bundle declares a classic cluster.
- **Consequences:** Run each notebook with **Run all** in setup → Bronze → Silver → Gold order. Package installation is repeated per notebook environment, but failures remain local and visible. The optional bundle points to the same self-contained notebook entrypoints.

## DD033 — Read the checked-in Bronze JSON from the notebook working directory

- **Date:** 2026-08-20
- **Status:** Superseded by DD035
- **Decision:** Resolve repository files from the Databricks notebook current working directory. Read the single checked-in Bronze JSON with Python on the driver, then create the source Spark DataFrame explicitly. Keep Lakehouse Engine for Delta reads, Data Quality, and Delta writes.
- **Rationale:** On current Databricks runtimes, the notebook working directory is its containing Git-folder directory. `__file__` is not the correct notebook path contract, and Spark executors cannot reliably read Git-folder workspace files through a local `file:` URI.
- **Consequences:** Preserve the repository directory structure and run the notebooks from their Git folder. A missing JSON snapshot or parser module raises a direct `FileNotFoundError`; there is no alternate source fallback.

## DD034 — Establish an explicit six-document SFS ingestion pilot

- **Date:** 2026-08-20
- **Status:** Superseded by DD036
- **Decision:** Fetch LAS, MBL, Semesterlagen, Arbetstidslagen, Föräldraledighetslagen, and Diskrimineringslagen from their stable Riksdagen document endpoints as one all-or-nothing batch. Preserve exact XML responses under `data/source/sfs`, store source-shaped JSON under `data/bronze/sfs`, and bind each pair with SHA-256 in a manifest.
- **Rationale:** Six structurally varied, employment-related laws expose parser assumptions without introducing the scope and ambiguity of every SFS document. Separating exact API bytes from Bronze JSON keeps source authority distinct from the first queryable representation.
- **Consequences:** `products.allegoria.sfs_ingestion` is the explicit refresh entrypoint and uses no new dependency. Existing LAS paths remain the active Databricks fixture until the multi-document Bronze schema is approved. Refreshing the pilot replaces its checked-in snapshots and retrieval timestamp; Git history retains earlier committed versions.

## DD035 — Use one shared SFS table per medallion layer

- **Date:** 2026-08-20
- **Status:** Active; supersedes DD028 and DD033
- **Decision:** Store every selected law in `bronze_allegoria.sfs_documents`, every parsed provision in `silver_allegoria.sfs_provisions`, and the neutral profile in `gold_allegoria.sfs_provision_summary`. Use descriptive notebook entrypoints `setup_catalog.py`, `bronze_sfs.py`, `silver_sfs.py`, and `gold_sfs.py` under responsibility-named folders.
- **Rationale:** A table per law would duplicate schemas, jobs, and transformations and make cross-law retrieval harder. One row per legal entity keeps law identity in `document_id` while schemas represent data responsibility.
- **Consequences:** The active notebooks and LAS regression test read the same checked-in SFS corpus. The old duplicate `data/source/las` and `data/bronze/las` paths are removed. All three Delta tables are overwritten as one reproducible current-snapshot dataset during development.

## DD036 — Expand the source corpus to 50 full law payloads

- **Date:** 2026-08-20
- **Status:** Active; supersedes DD034
- **Decision:** Always include the six employment-related seed laws and fill the corpus to 50 with the newest SFS titles containing `lag (` or `balk (`, excluding titles containing `förordning`. Preserve exact XML separately and also retain lossless `raw_xml`, decoded text, HTML, metadata, payload size, source URLs, and SHA-256 in each Bronze JSON and Delta row.
- **Rationale:** Fifty structurally varied laws are large enough to expose source-contract assumptions while remaining inspectable. Keeping the complete payload in Bronze makes every snapshot searchable by law ID without sacrificing byte-level provenance.
- **Consequences:** The manifest freezes the resolved IDs and selection rule. Ingestion is all-or-nothing, prunes generated files outside the resolved manifest, and uses `document_snapshot_id = document_id + source_sha256`. Refreshes can change the recent 44 laws and therefore require test and schema review.

## DD037 — Preserve optional and repeated SFS structures explicitly

- **Date:** 2026-08-20
- **Status:** Active
- **Decision:** Model a missing SFS subtitle as null and a missing transitional-provisions section as zero transition rows. If a transition section exists but cannot be parsed, fail. Preserve repeated paragraph anchors as separate rows and record their deterministic `source_anchor_occurrence`; never drop them as duplicates.
- **Rationale:** In the 50-law snapshot, 39 documents lack a subtitle, 27 lack a transition section, and 45 source anchors are reused. Reused anchors include future effective wordings and source collisions, so deduplication would delete legal content.
- **Consequences:** Derived `provision_id` values add an occurrence suffix after the first repeated anchor. Silver validates unique derived IDs and complete document coverage while retaining the original `source_anchor` for traceability.

## DD038 — Keep operational paths private and use layered lineage

- **Date:** 2026-08-20
- **Status:** Active
- **Decision:** Do not persist the Databricks Git-folder URI in Bronze. Retain the portable `source_raw_file`, official source URLs, `document_snapshot_id`, and `source_sha256`; recompute `sha2(raw_xml, 256)` in Bronze and fail on mismatch. Add `provision_text_sha256 = sha2(text, 256)` in Silver to distinguish derived-text identity from raw-document identity. Name processing timestamps by layer and carry snapshot lineage into the Gold profile.
- **Rationale:** A user-specific Workspace path is neither source provenance nor a stable data contract. Content identity, official URLs, layer timestamps, Delta history, and Unity Catalog lineage each answer a distinct lineage question without exposing the operator's path.
- **Consequences:** Bronze uses `bronze_ingested_at`; Silver carries it and adds `silver_transformed_at`; Gold carries both and adds `gold_aggregated_at`. Existing tables must be overwritten by rerunning Bronze, Silver, and Gold to remove the old `source_file`, `ingested_at`, and `refreshed_at` columns.

## DD039 — Add source-faithful Gold retrieval chunks

- **Date:** 2026-08-21
- **Status:** Active; supersedes DD029 and refines DD011, DD012, and DD035 for the 50-law PySpark pipeline
- **Decision:** Keep `sfs_provision_summary` as an independent profile and add `gold_allegoria.sfs_retrieval_chunks`. Keep complete provisions whose hierarchy-prefixed retrieval text is at most 2,000 characters; split only longer provisions, greedily, at preserved blank-line boundaries. Store clean `content` separately from `retrieval_text`, and require ordered chunks to reconstruct Silver text exactly.
- **Rationale:** The checked 1,952-provision corpus requires splitting only 11 provisions and produces 1,967 focused chunks without cutting a legal block. A separate consumer-ready table allows retrieval formatting and indexing to evolve without changing the canonical Silver legal units.
- **Consequences:** Chunk IDs extend readable provision IDs, all source and transformation hashes remain traceable, retrieval size and reconstruction failures stop the pipeline, and Change Data Feed is enabled for later Delta Sync indexing. Symbols, claims, metaphors, semantic labels, embeddings, and search indexes are not part of chunking; symbol semantics remain a later measured refinement after grounded retrieval works.

## DD040 — Add a v2 selection pool without touching the frozen v1 snapshot

- **Date:** 2026-09-10
- **Status:** Active; additive to DD036, which is not superseded
- **Decision:** Build a larger SFS pool solely to hand-pick corpus specimens from, resolved by the same rule as DD036 — the six employment seed laws, then the newest SFS titles containing `lag (` or `balk (` with `förordning` excluded — but filled to 500 instead of 50. The pool is described by its own `data/source/sfs/manifest_v2.json`. The v1 snapshot, `data/source/sfs/manifest.json`, and the 50 committed source and Bronze files are not edited, regenerated, or pruned, and the local Silver assertions of 50 documents and 1,952 provisions continue to hold when the scripts run against v1.
- **Rationale:** Selecting 20–40 twinned pairs from 460 candidates over 44 laws over-samples whichever statutes happen to be verbose; a wider pool gives more room to choose clean three-part specimens. A larger pool is not a larger experiment: the corpus size is set by how much can be hand-annotated, not by how much text is available.
- **Consequences:** The v2 payloads are ~70 MB and stay under gitignored `data/local/pool_v2/`; only the manifest, which carries the resolved IDs, titles, versions and SHA-256 hashes, is committed, so the pool is reproducible from git without the repository carrying the bytes. `scripts/ingest_pool_v2.py` writes per document rather than all-or-nothing so a 500-call run is resumable, pins the resolved ID list on first run so `newest 500` cannot drift between runs, and spaces requests by a configurable delay defaulting to 0.5s. Every response is still validated by `parse_sfs_xml` before that document is written, and a document that fails validation is recorded in `failures.json` and skipped rather than ending the run. `scripts/build_silver.py`, `build_tables.py` and `query.py` take `--pool v1|v2`; v1 keeps its hard expected counts and v2 has none, because the pool grows whenever it is re-fetched. v2 is a superset of v1 by construction, but re-fetching a law can return a newer consolidated version, so the two pools may hold different `document_snapshot_id` values for the same `document_id`.
