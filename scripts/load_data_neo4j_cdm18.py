from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from neo4j import GraphDatabase, ManagedTransaction


DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"
BATCH_SIZE = 5_000

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "4570176501"


def normalize_uuid(value: Any) -> str | None:
    """Return a valid canonical UUID string, or None."""
    if value is None:
        return None

    if isinstance(value, str):
        try:
            return str(UUID(value))
        except (ValueError, TypeError):
            return None

    if isinstance(value, dict):
        for key, nested_value in value.items():
            short_key = key.rsplit(".", 1)[-1].lower()

            if short_key in {"uuid", "id"}:
                result = normalize_uuid(nested_value)
                if result:
                    return result

        for nested_value in value.values():
            result = normalize_uuid(nested_value)
            if result:
                return result

    if isinstance(value, list):
        for nested_value in value:
            result = normalize_uuid(nested_value)
            if result:
                return result

    return None


def datum_kind(full_key: str) -> str:
    """Extract the CDM class from a fully qualified Avro key."""
    return full_key.rsplit(".", 1)[-1]


def node_type(kind: str, item: dict[str, Any]) -> str:
    """
    Match the PostgreSQL loader's type selection.

    Examples:
    SUBJECT_PROCESS
    FILE_OBJECT_BLOCK
    NetFlowObject
    MemoryObject
    """
    value = item.get("type")
    return str(value if value is not None else kind)[:50]


def event_timestamp(item: dict[str, Any]) -> int:
    value = item.get("timestampNanos", item.get("ts", 0))

    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def create_nodes(
    tx: ManagedTransaction,
    rows: list[dict[str, Any]],
) -> int:
    result = tx.run(
        """
        UNWIND $rows AS row
        MERGE (n:Node {uuid: row.uuid})
        ON CREATE SET n.type = row.type
        ON MATCH SET n.type = row.type
        """,
        rows=rows,
    )
    summary = result.consume()
    return summary.counters.nodes_created


def create_edges(
    tx: ManagedTransaction,
    rows: list[dict[str, Any]],
) -> int:
    result = tx.run(
        """
        UNWIND $rows AS row
        MATCH (src:Node {uuid: row.src})
        MATCH (dst:Node {uuid: row.dst})
        CREATE (src)-[:EDGE {
            type: row.type,
            ts: row.ts
        }]->(dst)
        """,
        rows=rows,
    )
    summary = result.consume()
    return summary.counters.relationships_created


def load_nodes(driver) -> tuple[int, int]:
    processed_lines = 0
    created_nodes = 0
    batch: list[dict[str, Any]] = []

    with driver.session(database="neo4j") as session:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                processed_lines = line_number

                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                datum = record.get("datum")
                if not isinstance(datum, dict):
                    continue

                for full_key, item in datum.items():
                    if not isinstance(item, dict):
                        continue

                    kind = datum_kind(full_key)

                    # Events are relationships, not graph nodes.
                    if "Event" in kind:
                        continue

                    entity_uuid = normalize_uuid(item.get("uuid"))
                    if not entity_uuid:
                        continue

                    batch.append(
                        {
                            "uuid": entity_uuid,
                            "type": node_type(kind, item),
                        }
                    )

                if len(batch) >= BATCH_SIZE:
                    created_nodes += session.execute_write(
                        create_nodes,
                        batch,
                    )
                    batch.clear()

                if line_number % 100_000 == 0:
                    print(
                        f"[Nodes] {line_number:,} lines processed; "
                        f"{created_nodes:,} nodes created"
                    )

            if batch:
                created_nodes += session.execute_write(
                    create_nodes,
                    batch,
                )
                batch.clear()

    return processed_lines, created_nodes


def load_edges(driver) -> tuple[int, int, int]:
    parsed_events = 0
    created_edges = 0
    batch: list[dict[str, Any]] = []

    with driver.session(database="neo4j") as session:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                datum = record.get("datum")
                if not isinstance(datum, dict):
                    continue

                for full_key, event in datum.items():
                    if not isinstance(event, dict):
                        continue

                    kind = datum_kind(full_key)

                    if "Event" not in kind:
                        continue

                    source_uuid = normalize_uuid(event.get("subject"))
                    destination_uuid = normalize_uuid(
                        event.get("predicateObject")
                    )

                    if not source_uuid or not destination_uuid:
                        continue

                    parsed_events += 1

                    batch.append(
                        {
                            "src": source_uuid,
                            "dst": destination_uuid,
                            "type": str(
                                event.get("type") or kind
                            )[:50],
                            "ts": event_timestamp(event),
                        }
                    )

                if len(batch) >= BATCH_SIZE:
                    created_edges += session.execute_write(
                        create_edges,
                        batch,
                    )
                    batch.clear()

                if line_number % 100_000 == 0:
                    print(
                        f"[Edges] {line_number:,} lines processed; "
                        f"{parsed_events:,} events parsed; "
                        f"{created_edges:,} relationships created"
                    )

            if batch:
                created_edges += session.execute_write(
                    create_edges,
                    batch,
                )
                batch.clear()

    unmatched_events = parsed_events - created_edges
    return parsed_events, created_edges, unmatched_events


def clear_graph(driver) -> None:
    with driver.session(database="neo4j") as session:
        result = session.run(
            """
            MATCH (n)
            DETACH DELETE n
            """
        )
        result.consume()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load DARPA THEIA CDM18 into Neo4j."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing graph nodes and relationships first.",
    )
    args = parser.parse_args()

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    start_time = time.perf_counter()

    try:
        driver.verify_connectivity()

        if args.reset:
            print("Clearing existing Neo4j graph...")
            clear_graph(driver)

        print(f"Dataset: {DATA_FILE}")
        print("Pass 1/2: loading Neo4j nodes...")

        processed_lines, created_nodes = load_nodes(driver)

        print("Pass 2/2: loading Neo4j relationships...")

        parsed_events, created_edges, unmatched_events = load_edges(
            driver
        )

        elapsed = time.perf_counter() - start_time

        print("\n" + "=" * 60)
        print("Neo4j loading completed")
        print("=" * 60)
        print(f"Lines processed:       {processed_lines:,}")
        print(f"Nodes created:         {created_nodes:,}")
        print(f"Events parsed:         {parsed_events:,}")
        print(f"Relationships created: {created_edges:,}")
        print(f"Unmatched events:      {unmatched_events:,}")
        print(f"Elapsed seconds:       {elapsed:.3f}")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
