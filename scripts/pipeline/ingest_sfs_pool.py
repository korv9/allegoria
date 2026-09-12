"""Fetch the v2 SFS selection pool from Riksdagen.

The v1 50-law snapshot under `data/source/sfs` and `data/bronze/sfs` is frozen.
This script never writes into either directory: the v2 payloads land under
`data/local/pool_v2/` (gitignored, ~70 MB at 500 laws) and only the manifest --
ids, titles, versions and hashes, a few hundred KB -- is written back to
`data/source/sfs/manifest_v2.json` so the pool stays reproducible from git.

    python scripts/pipeline/ingest_sfs_pool.py                 # 500 laws, 0.5s apart
    python scripts/pipeline/ingest_sfs_pool.py --count 100
    python scripts/pipeline/ingest_sfs_pool.py                 # re-run: skips what exists

A larger pool is for SELECTING specimens, not for running a larger experiment.
The corpus stays 20-40 hand-twinned pairs regardless of how big this gets.

Three differences from `products/allegoria/sfs_ingestion.py`, which is left
untouched:

1. It writes per document instead of materialising all 50 at the end. A 500-call
   run cannot hold everything and discard it on the last failure, and resuming
   needs the completed work to be on disk. Each response is still fully
   validated by `parse_sfs_xml` before that document is written.
2. The resolved id list is pinned to disk on the first run. "Newest 500" moves
   as Riksdagen publishes; re-running must continue the same pool, not drift.
3. Requests are spaced by a delay, and an existing document is skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from products.allegoria.sfs_ingestion import (
    DATA_URL_TEMPLATE,
    LIST_URL,
    SEED_DOCUMENT_IDS,
    _fetch_bytes,
    _is_law_title,
    _required_list_value,
    parse_sfs_xml,
)
from simulacria.pipeline.silver import PROJECT_ROOT

POOL_DIR = PROJECT_ROOT / "data" / "local" / "pool_v2"
MANIFEST_PATH = PROJECT_ROOT / "data" / "source" / "sfs" / "manifest_v2.json"
DEFAULT_COUNT = 500
DEFAULT_DELAY = 0.5

SELECTION_RULE = (
    "The six employment seed laws, then the newest SFS titles containing "
    "'lag (' or 'balk (' with 'förordning' excluded, until the target count is "
    "reached. Identical to the v1 rule; only the target count differs, so the "
    "v2 pool is a superset of v1 by construction."
)


def discover_document_ids(target_count: int, delay: float) -> list[str]:
    """Resolve the pool membership: seeds first, then newest law titles."""
    selected = list(SEED_DOCUMENT_IDS)
    seen = set(selected)
    page = 1

    while len(selected) < target_count:
        query = urlencode(
            {
                "doktyp": "sfs",
                "sort": "datum",
                "sortorder": "desc",
                "utformat": "json",
                "p": page,
            }
        )
        payload = json.loads(_fetch_bytes(f"{LIST_URL}?{query}", "application/json"))
        document_list = payload.get("dokumentlista")
        if not isinstance(document_list, dict):
            raise TypeError(f"SFS list page {page} has no dokumentlista object")
        documents = document_list.get("dokument")
        if not isinstance(documents, list) or not documents:
            raise ValueError(f"SFS list page {page} contains no documents")

        for document in documents:
            if not isinstance(document, dict):
                raise TypeError(f"SFS list page {page} contains an invalid document")
            document_id = _required_list_value(document, "dok_id", page)
            title = _required_list_value(document, "titel", page)
            if _is_law_title(title) and document_id not in seen:
                selected.append(document_id)
                seen.add(document_id)
                if len(selected) == target_count:
                    break

        print(f"  discovery page {page}: {len(selected)}/{target_count} ids resolved")
        page += 1
        time.sleep(delay)

    return selected


def pinned_document_ids(pool_dir: Path, target_count: int, delay: float) -> list[str]:
    """Pin the pool membership on first run so a resume continues the same pool."""
    pin = pool_dir / "document_ids.json"
    if pin.is_file():
        pinned = json.loads(pin.read_text(encoding="utf-8"))
        ids = [str(document_id) for document_id in pinned["document_ids"]]
        print(
            f"Using pinned pool of {len(ids)} ids from {pin.name} (resolved {pinned['pinned_at']})"
        )
        return ids

    ids = discover_document_ids(target_count, delay)
    pool_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        pin,
        json.dumps(
            {
                "pinned_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "target_count": target_count,
                "selection_rule": SELECTION_RULE,
                "document_ids": ids,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return ids


def fetch_pool(pool_dir: Path, document_ids: list[str], delay: float) -> dict[str, int]:
    source_dir, bronze_dir = pool_dir / "source", pool_dir / "bronze"
    source_dir.mkdir(parents=True, exist_ok=True)
    bronze_dir.mkdir(parents=True, exist_ok=True)

    stats = {"fetched": 0, "skipped": 0, "failed": 0}
    failures: list[str] = []

    for index, document_id in enumerate(document_ids, start=1):
        raw_path = source_dir / f"{document_id}.xml"
        bronze_path = bronze_dir / f"{document_id}.json"
        if raw_path.is_file() and bronze_path.is_file():
            stats["skipped"] += 1
            continue

        source_url = DATA_URL_TEMPLATE.format(document_id=document_id)
        try:
            raw_xml = _fetch_bytes(source_url, accept="application/xml")
            retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
            # parse_sfs_xml is the validator: id match, sfs/sfst type, lossless
            # UTF-8, required fields present. Nothing is written until it passes.
            bronze = parse_sfs_xml(raw_xml, document_id, source_url, retrieved_at)
        except Exception as error:  # noqa: BLE001 - one bad law must not end the run
            stats["failed"] += 1
            failures.append(f"{document_id}: {type(error).__name__}: {error}")
            print(f"  [{index}/{len(document_ids)}] FAILED {document_id}: {error}")
            time.sleep(delay)
            continue

        _atomic_write(raw_path, raw_xml)
        _atomic_write(bronze_path, json.dumps(bronze, ensure_ascii=False, indent=2) + "\n")
        stats["fetched"] += 1
        if stats["fetched"] % 25 == 0:
            print(f"  [{index}/{len(document_ids)}] fetched {stats['fetched']} new documents")
        time.sleep(delay)

    if failures:
        _atomic_write(
            pool_dir / "failures.json",
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n",
        )
    return stats


def write_manifest(pool_dir: Path, document_ids: list[str], manifest_path: Path) -> int:
    """Describe exactly the documents that made it into the pool."""
    bronze_dir = pool_dir / "bronze"
    entries = []
    for document_id in document_ids:
        bronze_path = bronze_dir / f"{document_id}.json"
        if not bronze_path.is_file():
            continue
        bronze = json.loads(bronze_path.read_text(encoding="utf-8"))
        raw_bytes = (pool_dir / "source" / f"{document_id}.xml").read_bytes()
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        if raw_sha256 != bronze["source_sha256"]:
            raise SystemExit(
                f"{document_id}: stored XML hash {raw_sha256} does not match the "
                f"bronze record {bronze['source_sha256']}"
            )
        entries.append(
            {
                "document_id": bronze["document_id"],
                "title": bronze["title"],
                "version": bronze["version"],
                "source_data_url": bronze["source_data_url"],
                "raw_file": bronze["source_raw_file"],
                "raw_sha256": raw_sha256,
            }
        )

    manifest = {
        "dataset_id": "swedish-law-pool-v2",
        "purpose": (
            "A larger pool to hand-pick corpus specimens from. Not a larger "
            "experiment: the twinned corpus stays 20-40 pairs."
        ),
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "Sveriges riksdag open data",
        "payload_location": (
            "data/local/pool_v2/ -- gitignored; rebuild with scripts/pipeline/ingest_sfs_pool.py"
        ),
        "supersedes": None,
        "relation_to_v1": (
            "Additive. data/source/sfs/manifest.json and the 50-law v1 snapshot "
            "are unchanged and remain the regression corpus."
        ),
        "selection": {"target_count": len(document_ids), "rule": SELECTION_RULE},
        "documents": entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return len(entries)


def _atomic_write(path: Path, payload: bytes | str) -> None:
    """Write via a temp file so an interrupted run leaves no half-file behind.

    A truncated payload that looks complete would be skipped on resume.
    """
    temporary = path.with_suffix(path.suffix + ".tmp")
    if isinstance(payload, bytes):
        temporary.write_bytes(payload)
    else:
        temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--pool-dir", type=Path, default=POOL_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    if args.delay < 0.1:
        raise SystemExit("--delay below 0.1s is impolite to Riksdagen; refusing")

    document_ids = pinned_document_ids(args.pool_dir, args.count, args.delay)
    stats = fetch_pool(args.pool_dir, document_ids, args.delay)
    in_manifest = write_manifest(args.pool_dir, document_ids, args.manifest)

    print(
        f"POOL v2 | {len(document_ids)} ids | fetched {stats['fetched']}, "
        f"skipped {stats['skipped']}, failed {stats['failed']} | "
        f"{in_manifest} documents in {args.manifest.name}"
    )
    if stats["failed"]:
        print(f"  see {args.pool_dir / 'failures.json'} -- re-run to retry them")


if __name__ == "__main__":
    main()
