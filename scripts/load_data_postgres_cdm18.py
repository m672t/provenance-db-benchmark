from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg2
from psycopg2.extras import execute_values


DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"
BATCH_SIZE = 5_000


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
        # CDM18 references commonly contain a nested Avro UUID key.
        for key, nested_value in value.items():
            short_key = key.rsplit(".", 1)[-1]

            if short_key.lower() in {"uuid", "id"}:
                result = normalize_uuid(nested_value)
                if result:
                    return result

        # Fallback recursive search.
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
    """Extract CDM class name from a fully qualified Avro key."""
    return full_key.rsplit(".", 1)[-1]


def node_type(kind: str, item: dict[str, Any]) -> str:
    """
    Preserve specific CDM subtype where available.
    Otherwise use the datum class, e.g. NetFlowObject or Host.
    """
    value = item.get("type")
    return str(value if value is not None else kind)[:50]


def event_timestamp(item: dict[str, Any]) -> int:
    value = item.get("timestampNanos", item.get("ts", 0))

    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def flush_nodes(cursor, rows: list[tuple[str, str]]) -> int:
    if not rows:
        return 0

    execute_values(
        cursor,
        """
        INSERT INTO nodes (uuid, type)
        VALUES %s
        ON CONFLICT (uuid) DO NOTHING
        """,
        rows,
        page_size=BATCH_SIZE,
    )

    inserted = cursor.rowcount
    rows.clear()
    return max(inserted, 0)


def flush_edges(
    cursor,
    rows: list[tuple[str, str, str, int]],
) -> int:
    if not rows:
        return 0

    # The JOINs preserve the foreign-key model and omit events whose
    # source or destination entity is absent from this dataset slice.
    execute_values(
        cursor,
        """
        INSERT INTO edges (src, dst, type, ts)
        SELECT
            values_table.src::uuid,
            values_table.dst::uuid,
            values_table.event_type,
            values_table.event_ts::bigint
        FROM (VALUES %s)
            AS values_table(src, dst, event_type, event_ts)
        JOIN nodes source_node
          ON source_node.uuid = values_table.src::uuid
        JOIN nodes destination_node
          ON destination_node.uuid = values_table.dst::uuid
        """,
        rows,
        page_size=BATCH_SIZE,
    )

    inserted = cursor.rowcount
    rows.clear()
    return max(inserted, 0)


def load_nodes(connection) -> tuple[int, int]:
    """First pass: load all non-event entities that have UUIDs."""
    processed_lines = 0
    inserted_nodes = 0
    node_batch: list[tuple[str, str]] = []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        with connection.cursor() as cursor:
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

                    # Events have UUIDs too, but they are relationships,
                    # not nodes in this project model.
                    if "Event" in kind:
                        continue

                    entity_uuid = normalize_uuid(item.get("uuid"))
                    if not entity_uuid:
                        continue

                    node_batch.append(
                        (entity_uuid, node_type(kind, item))
                    )

                if len(node_batch) >= BATCH_SIZE:
                    inserted_nodes += flush_nodes(cursor, node_batch)
                    connection.commit()

                if line_number % 100_000 == 0:
                    print(
                        f"[Nodes] {line_number:,} lines processed; "
                        f"{inserted_nodes:,} nodes inserted"
                    )

            inserted_nodes += flush_nodes(cursor, node_batch)
            connection.commit()

    return processed_lines, inserted_nodes


def load_edges(connection) -> tuple[int, int, int]:
    """
    Second pass: convert CDM Event records into directed edges:
    subject -> predicateObject.
    """
    parsed_events = 0
    inserted_edges = 0
    edge_batch: list[tuple[str, str, str, int]] = []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        with connection.cursor() as cursor:
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

                    edge_batch.append(
                        (
                            source_uuid,
                            destination_uuid,
                            str(event.get("type") or kind)[:50],
                            event_timestamp(event),
                        )
                    )

                if len(edge_batch) >= BATCH_SIZE:
                    inserted_edges += flush_edges(cursor, edge_batch)
                    connection.commit()

                if line_number % 100_000 == 0:
                    print(
                        f"[Edges] {line_number:,} lines processed; "
                        f"{parsed_events:,} valid events parsed; "
                        f"{inserted_edges:,} edges inserted"
                    )

            inserted_edges += flush_edges(cursor, edge_batch)
            connection.commit()

    return parsed_events, inserted_edges, parsed_events - inserted_edges


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load DARPA THEIA CDM18 into PostgreSQL."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear nodes and edges before loading.",
    )
    args = parser.parse_args()

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    connection = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="4570176501",
        host="localhost",
        port="5432",
    )

    start_time = time.perf_counter()

    try:
        if args.reset:
            with connection.cursor() as cursor:
                cursor.execute(
                    "TRUNCATE TABLE edges, nodes "
                    "RESTART IDENTITY CASCADE"
                )
            connection.commit()
            print("PostgreSQL tables cleared.")

        print(f"Dataset: {DATA_FILE}")
        print("Pass 1/2: loading nodes...")

        processed_lines, inserted_nodes = load_nodes(connection)

        print("Pass 2/2: loading edges...")

        parsed_events, inserted_edges, unmatched_events = load_edges(
            connection
        )

        elapsed = time.perf_counter() - start_time

        print("\n" + "=" * 60)
        print("PostgreSQL loading completed")
        print("=" * 60)
        print(f"Lines processed:       {processed_lines:,}")
        print(f"Nodes inserted:        {inserted_nodes:,}")
        print(f"Events parsed:         {parsed_events:,}")
        print(f"Edges inserted:        {inserted_edges:,}")
        print(f"Unmatched events:      {unmatched_events:,}")
        print(f"Elapsed seconds:       {elapsed:.3f}")

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
