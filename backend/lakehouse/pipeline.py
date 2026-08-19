from __future__ import annotations

from .bronze import build_bronze_df, write_bronze_df
from .gold import build_gold_df, write_gold_df
from .quality import build_quality_df, validate_las_data, write_quality_df
from .silver import build_silver_df, write_silver_df


def build_las_data() -> tuple[int, int]:
    bronze_df = build_bronze_df()
    silver_df = build_silver_df(bronze_df)
    gold_df = build_gold_df(bronze_df, silver_df)

    validate_las_data(bronze_df, silver_df, gold_df)
    quality_df = build_quality_df(silver_df, gold_df)

    write_bronze_df(bronze_df)
    write_silver_df(silver_df)
    write_gold_df(gold_df)
    write_quality_df(quality_df)

    return len(silver_df), len(gold_df)


def main() -> None:
    provision_count, chunk_count = build_las_data()
    print(f"Built LAS data: {provision_count} Silver provisions, {chunk_count} Gold chunks")


if __name__ == "__main__":
    main()
