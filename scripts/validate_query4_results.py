from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg2
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parent.parent

POSTGRES_QUERY_FILE = (
    ROOT / "postgres" / "queries" / "query4_threat_scoring.sql"
)

NEO4J_QUERY_FILE = (
    ROOT / "neo4j" / "queries" / "query4_threat_scoring.cypher"
)

OUTPUT_FILE = (
    ROOT / "results" / "query4" / "result_validation.txt"
)


def load_query(path: Path) -> str:
    query = path.read_text(encoding="utf-8").strip()

    # Neo4j drivers do not need the final semicolon.
    return query[:-1] if query.endswith(";") else query


def normalize_postgres_row(row: tuple[Any, ...]) -> tuple[Any, ...]:
    return (
        str(row[0]),  # UUID
        str(row[1]),  # target type
        int(row[2]),
        int(row[3]),
        int(row[4]),
        int(row[5]),
    )


def normalize_neo4j_record(record: Any) -> tuple[Any, ...]:
    return (
        str(record["target_uuid"]),
        str(record["target_type"]),
        int(record["distinct_source_processes"]),
        int(record["execute_count"]),
        int(record["write_count"]),
        int(record["threat_score"]),
    )


def read_postgres_results() -> list[tuple[Any, ...]]:
    query = load_query(POSTGRES_QUERY_FILE)

    connection = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="4570176501",
        host="localhost",
        port="5432",
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return [
                normalize_postgres_row(row)
                for row in cursor.fetchall()
            ]
    finally:
        connection.close()


def read_neo4j_results() -> list[tuple[Any, ...]]:
    query = load_query(NEO4J_QUERY_FILE)

    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "4570176501"),
    )

    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query)
            return [
                normalize_neo4j_record(record)
                for record in result
            ]
    finally:
        driver.close()


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("Reading PostgreSQL results...")
    postgres_rows = read_postgres_results()

    print("Reading Neo4j results...")
    neo4j_rows = read_neo4j_results()

    mismatches: list[
        tuple[int, tuple[Any, ...] | None, tuple[Any, ...] | None]
    ] = []

    maximum_length = max(
        len(postgres_rows),
        len(neo4j_rows),
    )

    for index in range(maximum_length):
        postgres_row = (
            postgres_rows[index]
            if index < len(postgres_rows)
            else None
        )

        neo4j_row = (
            neo4j_rows[index]
            if index < len(neo4j_rows)
            else None
        )

        if postgres_row != neo4j_row:
            mismatches.append(
                (index + 1, postgres_row, neo4j_row)
            )

            # Ten examples are enough for diagnosis.
            if len(mismatches) >= 10:
                break

    identical = (
        len(postgres_rows) == len(neo4j_rows)
        and not mismatches
    )

    report_lines = [
        "Query 4 result validation",
        "=" * 50,
        f"PostgreSQL rows: {len(postgres_rows):,}",
        f"Neo4j rows:      {len(neo4j_rows):,}",
        f"Exact match:     {'YES' if identical else 'NO'}",
        "",
    ]

    if mismatches:
        report_lines.append("First mismatches:")

        for position, postgres_row, neo4j_row in mismatches:
            report_lines.extend(
                [
                    f"Row position: {position}",
                    f"PostgreSQL:   {postgres_row}",
                    f"Neo4j:        {neo4j_row}",
                    "",
                ]
            )
    else:
        report_lines.append(
            "All rows, metric values, scores, and ordering match."
        )

    report = "\n".join(report_lines)

    OUTPUT_FILE.write_text(report, encoding="utf-8")

    print()
    print(report)
    print(f"\nSaved to: {OUTPUT_FILE}")

    if not identical:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
