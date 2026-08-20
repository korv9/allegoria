from __future__ import annotations

from pathlib import Path

import pandas as pd

from .gold import load_gold_df
from .lexical import LEXICAL_RETRIEVER_NAME, LexicalRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_PATH = (
    PROJECT_ROOT / "data" / "evaluation" / "retrieval" / "las.jsonl"
)

EVALUATION_COLUMNS = [
    "query_id",
    "query",
    "query_type",
    "relevant_provision_ids",
]
QUERY_TYPES = {"legal_terms", "natural_language"}
RESULT_COLUMNS = [
    "retriever",
    "query_id",
    "query",
    "query_type",
    "top_k",
    "relevant_provision_ids",
    "retrieved_provision_ids",
    "hit",
    "reciprocal_rank",
]


def load_evaluation_df(path: Path = EVALUATION_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Retrieval evaluation data does not exist: {path}")

    evaluation_df = pd.read_json(path, lines=True)
    missing_columns = set(EVALUATION_COLUMNS) - set(evaluation_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Retrieval evaluation is missing columns: {missing}")

    evaluation_df = evaluation_df.loc[:, EVALUATION_COLUMNS]
    evaluation_df = evaluation_df.astype(
        {
            "query_id": "string",
            "query": "string",
            "query_type": "string",
        }
    )

    if evaluation_df.empty:
        raise ValueError("Retrieval evaluation contains no queries")
    if evaluation_df[["query_id", "query", "query_type"]].isna().any().any():
        raise ValueError("Retrieval evaluation has missing required values")
    if evaluation_df["query_id"].duplicated().any():
        raise ValueError("Retrieval evaluation has duplicate query IDs")
    if evaluation_df["query"].duplicated().any():
        raise ValueError("Retrieval evaluation has duplicate queries")
    if evaluation_df["query"].eq("").any():
        raise ValueError("Retrieval evaluation has an empty query")
    unknown_query_types = set(evaluation_df["query_type"]) - QUERY_TYPES
    if unknown_query_types:
        unknown = ", ".join(sorted(unknown_query_types))
        raise ValueError(f"Retrieval evaluation has unknown query types: {unknown}")

    valid_relevance_lists = evaluation_df["relevant_provision_ids"].map(
        _is_non_empty_string_list
    )
    if not valid_relevance_lists.all():
        raise ValueError("Retrieval evaluation has a query without relevance labels")

    return evaluation_df


def validate_relevance_labels(
    evaluation_df: pd.DataFrame, gold_df: pd.DataFrame
) -> None:
    available_ids = set(gold_df["provision_id"])
    labeled_ids = {
        provision_id
        for provision_ids in evaluation_df["relevant_provision_ids"]
        for provision_id in provision_ids
    }
    unknown_ids = labeled_ids - available_ids
    if unknown_ids:
        unknown = ", ".join(sorted(unknown_ids))
        raise ValueError(f"Retrieval evaluation has unknown provision IDs: {unknown}")


def evaluate_retriever(
    retriever: LexicalRetriever,
    evaluation_df: pd.DataFrame,
    top_k: int = 3,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for evaluation in evaluation_df.to_dict(orient="records"):
        search_df = retriever.search(query=evaluation["query"], top_k=top_k)
        retrieved_ids = search_df["provision_id"].tolist()
        relevant_ids = evaluation["relevant_provision_ids"]

        relevant_ranks = [
            rank
            for rank, provision_id in enumerate(retrieved_ids, start=1)
            if provision_id in relevant_ids
        ]
        first_relevant_rank = min(relevant_ranks) if relevant_ranks else None

        records.append(
            {
                "retriever": LEXICAL_RETRIEVER_NAME,
                "query_id": evaluation["query_id"],
                "query": evaluation["query"],
                "query_type": evaluation["query_type"],
                "top_k": top_k,
                "relevant_provision_ids": relevant_ids,
                "retrieved_provision_ids": retrieved_ids,
                "hit": first_relevant_rank is not None,
                "reciprocal_rank": (
                    1.0 / first_relevant_rank if first_relevant_rank else 0.0
                ),
            }
        )

    result_df = pd.DataFrame(records)
    result_df = result_df.astype(
        {
            "retriever": "string",
            "query_id": "string",
            "query": "string",
            "query_type": "string",
            "top_k": "int64",
            "hit": "bool",
            "reciprocal_rank": "float64",
        }
    )
    result_df = result_df.loc[:, RESULT_COLUMNS]

    return result_df


def summarize_evaluation(result_df: pd.DataFrame) -> pd.DataFrame:
    summary_df = result_df.groupby(
        ["retriever", "top_k"],
        as_index=False,
    ).agg(
        query_count=("query_id", "count"),
        hit_count=("hit", "sum"),
        hit_rate=("hit", "mean"),
        mean_reciprocal_rank=("reciprocal_rank", "mean"),
    )
    summary_df = summary_df.astype(
        {
            "retriever": "string",
            "top_k": "int64",
            "query_count": "int64",
            "hit_count": "int64",
            "hit_rate": "float64",
            "mean_reciprocal_rank": "float64",
        }
    )

    return summary_df


def summarize_evaluation_by_query_type(result_df: pd.DataFrame) -> pd.DataFrame:
    summary_df = result_df.groupby(
        ["retriever", "top_k", "query_type"],
        as_index=False,
    ).agg(
        query_count=("query_id", "count"),
        hit_count=("hit", "sum"),
        hit_rate=("hit", "mean"),
        mean_reciprocal_rank=("reciprocal_rank", "mean"),
    )
    summary_df = summary_df.astype(
        {
            "retriever": "string",
            "top_k": "int64",
            "query_type": "string",
            "query_count": "int64",
            "hit_count": "int64",
            "hit_rate": "float64",
            "mean_reciprocal_rank": "float64",
        }
    )

    return summary_df


def evaluate_las(top_k: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    gold_df = load_gold_df()
    evaluation_df = load_evaluation_df()
    validate_relevance_labels(evaluation_df, gold_df)

    with LexicalRetriever(gold_df) as retriever:
        result_df = evaluate_retriever(retriever, evaluation_df, top_k=top_k)

    summary_df = summarize_evaluation(result_df)
    return result_df, summary_df


def main() -> None:
    result_df, summary_df = evaluate_las()
    query_type_summary_df = summarize_evaluation_by_query_type(result_df)
    print(result_df.loc[:, ["query_id", "query_type", "hit", "reciprocal_rank"]])
    print()
    print(summary_df)
    print()
    print(query_type_summary_df)


def _is_non_empty_string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item) for item in value)
    )


if __name__ == "__main__":
    main()
