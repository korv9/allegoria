from __future__ import annotations

import argparse
import json
import sys

from .context import build_context_packet
from .lexical import LEXICAL_RETRIEVER_NAME, search_las


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Search the local LAS Gold data")
    parser.add_argument("query", nargs="+", help="Swedish LAS search query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--context-json",
        action="store_true",
        help="Print the versioned RAG context packet as JSON",
    )
    arguments = parser.parse_args()

    query = " ".join(arguments.query)
    result_df = search_las(query=query, top_k=arguments.top_k)

    if result_df.empty:
        print("No lexical matches")
        return

    if arguments.context_json:
        context_packet = build_context_packet(
            query=query,
            retriever=LEXICAL_RETRIEVER_NAME,
            result_df=result_df,
        )
        print(json.dumps(context_packet, ensure_ascii=False, indent=2))
        return

    for result in result_df.to_dict(orient="records"):
        print(
            f'{result["rank"]}. {result["label"]} | '
            f'score={result["score"]:.6f}'
        )
        print(result["heading"])
        print(result["content"])
        print(result["source_url"])
        print()


if __name__ == "__main__":
    main()
