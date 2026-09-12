"""Verify one registry model with a single cheap live call. Costs a fraction of a cent.

    python scripts/investigations/check_provider.py haiku-4-5
    python scripts/investigations/check_provider.py gpt-5-4-mini --schema

This is what `verified:` in configs/models.yaml means. It checks the four things
that have to hold before a model is trusted with a run's money:

1. the request this code builds is accepted,
2. the response decodes through the provider's decoder,
3. the returned model id matches the pinned request (no silent substitution),
4. usage is where the cost accounting looks for it.

With `--schema` it also asks for a structured answer and checks it parses, which
is the part a reader model depends on. Nothing is written into a run directory:
the response is saved under data/local/probes/, which is not experiment evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from simulacria.generation.models import by_name
from simulacria.generation.provider import (
    api_key,
    billed_cost,
    post_response,
    request_payload,
    response_text,
    with_schema,
)

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    },
}


def check(name: str, want_schema: bool) -> int:
    spec = by_name(name)
    key = api_key(ROOT, spec)
    payload = request_payload(
        spec,
        "Answer with the single word OK." if not want_schema else "Answer with JSON.",
        "Reply OK." if not want_schema else 'Reply with {"answer": "OK"}.',
        max_tokens=200,
    )
    if want_schema:
        with_schema(payload, SCHEMA)

    directory = ROOT / "data/local/probes" / ("provider-check-" + uuid4().hex[:12])
    directory.mkdir(parents=True)
    status, raw = post_response(payload, key)
    (directory / "response.json").write_bytes(raw)

    result = {
        "kind": "provider_check",
        "experiment_data": False,
        "at": datetime.now(UTC).isoformat(),
        "model": spec.record(),
        "http_status": status,
        "raw_sha256": sha256(raw).hexdigest(),
        "structured_output_requested": want_schema,
        "usd": billed_cost(raw, spec),
    }
    print(f"HTTP {status}  ({spec.provider}/{spec.model})")
    if status != 200:
        result["ok"] = False
        result["error_body_preview"] = raw[:200].decode("utf-8", "replace")
        print(f"FAILED: {result['error_body_preview']}")
    else:
        try:
            text, response = response_text(raw, spec)
            result.update(
                ok=True,
                returned_model=response.get("model"),
                usage=response.get("usage"),
                text_preview=text[:120],
                parses_as_json=bool(want_schema and json.loads(text)),
            )
            print(f"decoded OK, returned model {response.get('model')}")
            print(f"usage {response.get('usage')}  cost ${result['usd']:.6f}")
            print(f"text: {text[:120]!r}")
        except ValueError as error:
            result.update(ok=False, error=f"{type(error).__name__}: {error}")
            print(f"FAILED to decode: {result['error']}")

    (directory / "check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved: {directory}")
    if result.get("ok"):
        print(
            f"\nIf this looks right, set `verified: {datetime.now(UTC).date()}` on "
            f"`{spec.name}` in configs/models.yaml."
        )
        return 0
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="a registry name from configs/models.yaml")
    parser.add_argument("--schema", action="store_true", help="also check structured output")
    args = parser.parse_args()
    raise SystemExit(check(args.model, args.schema))
