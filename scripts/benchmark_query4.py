from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path
from typing import Callable

import psycopg2
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parent.parent

POSTGRES_QUERY_PATH = (
    ROOT / "postgres" / "queries" / "query4_threat_scoring.sql"
)

NEO4J_QUERY_PATH = (
    ROOT / "neo4j" / "queries" / "query4_threat_scoring.cypher"
)

RESULTS_DIRECTORY = ROOT / "results" / "query4"


def read_query(path: Path) -> str:
    query = path.read_text(encoding="utf-8").strip()
    return query[:-1] if query.endswith(";") else query


def benchmark_postgres(
    query: str,
    measured_runs: int,
) -> tuple[list[float], list[int]]:
    connection = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="4570176501",
        host="localhost",
        port="5432",
    )

    durations: list[float] = []
    row_counts: list[int] = []

    try:
        with connection.cursor() as cursor:
            print("PostgreSQL warm-up...")
            cursor.execute(query)
            cursor.fetchall()

            for run_number in range(1, measured_runs + 1):
                start = time.perf_counter()

                cursor.execute(query)
                rows = cursor.fetchall()

                elapsed_ms = (
                    time.perf_counter() - start
                ) * 1000

                durations.append(elapsed_ms)
                row_counts.append(len(rows))

                print(
                    f"PostgreSQL run {run_number}: "
                    f"{elapsed_ms:.3f} ms, "
                    f"{len(rows):,} rows"
                )
    finally:
        connection.close()

    return durations, row_counts


def benchmark_neo4j(
    query: str,
    measured_runs: int,
) -> tuple[list[float], list[int]]:
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "4570176501"),
    )

    durations: list[float] = []
    row_counts: list[int] = []

    try:
        with driver.session(database="neo4j") as session:
            print("Neo4j warm-up...")
            warmup_result = session.run(query)

            for _ in warmup_result:
                pass

            warmup_result.consume()

            for run_number in range(1, measured_runs + 1):
                start = time.perf_counter()

                result = session.run(query)
                row_count = sum(1 for _ in result)
                result.consume()

                elapsed_ms = (
                    time.perf_counter() - start
                ) * 1000

                durations.append(elapsed_ms)
                row_counts.append(row_count)

                print(
                    f"Neo4j run {run_number}: "
                    f"{elapsed_ms:.3f} ms, "
                    f"{row_count:,} rows"
                )
    finally:
        driver.close()

    return durations, row_counts


def write_results(
    state: str,
    database: str,
    durations: list[float],
    row_counts: list[int],
) -> None:
    output_path = (
        RESULTS_DIRECTORY / f"{database}_{state}_timings.csv"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "database",
                "state",
                "run",
                "elapsed_ms",
                "row_count",
            ]
        )

        for run_number, (duration, row_count) in enumerate(
            zip(durations, row_counts),
            start=1,
        ):
            writer.writerow(
                [
                    database,
                    state,
                    run_number,
                    f"{duration:.3f}",
                    row_count,
                ]
            )


def print_summary(
    database: str,
    durations: list[float],
    row_counts: list[int],
) -> None:
    print()
    print(f"{database} summary")
    print("-" * 40)
    print(f"Runs:       {len(durations)}")
    print(f"Rows:       {set(row_counts)}")
    print(f"Minimum:    {min(durations):.3f} ms")
    print(f"Maximum:    {max(durations):.3f} ms")
    print(f"Mean:       {statistics.mean(durations):.3f} ms")
    print(f"Median:     {statistics.median(durations):.3f} ms")
    print(
        f"Std. dev.:  "
        f"{statistics.stdev(durations):.3f} ms"
        if len(durations) > 1
        else "Std. dev.:  N/A"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Query 4 in PostgreSQL and Neo4j."
    )

    parser.add_argument(
        "--state",
        choices=["raw", "indexed"],
        required=True,
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=7,
    )

    args = parser.parse_args()

    if args.runs < 3:
        raise ValueError(
            "Use at least three measured runs."
        )

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    postgres_query = read_query(POSTGRES_QUERY_PATH)
    neo4j_query = read_query(NEO4J_QUERY_PATH)

    postgres_durations, postgres_rows = benchmark_postgres(
        postgres_query,
        args.runs,
    )

    neo4j_durations, neo4j_rows = benchmark_neo4j(
        neo4j_query,
        args.runs,
    )

    if set(postgres_rows) != {63018}:
        raise RuntimeError(
            f"Unexpected PostgreSQL row counts: "
            f"{postgres_rows}"
        )

    if set(neo4j_rows) != {63018}:
        raise RuntimeError(
            f"Unexpected Neo4j row counts: "
            f"{neo4j_rows}"
        )

    write_results(
        args.state,
        "postgres",
        postgres_durations,
        postgres_rows,
    )

    write_results(
        args.state,
        "neo4j",
        neo4j_durations,
        neo4j_rows,
    )

    print_summary(
        "PostgreSQL",
        postgres_durations,
        postgres_rows,
    )

    print_summary(
        "Neo4j",
        neo4j_durations,
        neo4j_rows,
    )


if __name__ == "__main__":
    main()
