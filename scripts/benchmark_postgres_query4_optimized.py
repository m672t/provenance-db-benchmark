from __future__ import annotations

import argparse

from benchmark_query4 import (
    ROOT,
    benchmark_postgres,
    print_summary,
    read_query,
    write_results,
)


QUERY_PATH = (
    ROOT
    / "postgres"
    / "queries"
    / "query4_threat_scoring_optimized.sql"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark optimized PostgreSQL Query 4."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=7,
    )
    args = parser.parse_args()

    query = read_query(QUERY_PATH)

    durations, row_counts = benchmark_postgres(
        query,
        args.runs,
    )

    if set(row_counts) != {63018}:
        raise RuntimeError(
            f"Unexpected row counts: {row_counts}"
        )

    write_results(
        "optimized",
        "postgres",
        durations,
        row_counts,
    )

    print_summary(
        "PostgreSQL optimized",
        durations,
        row_counts,
    )


if __name__ == "__main__":
    main()
