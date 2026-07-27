# provenance-db-benchmark

Benchmarking PostgreSQL and Neo4j on a DARPA THEIA CDM18 provenance dataset slice.

## Project overview

This repository compares relational and graph database performance for provenance-style security analytics workloads.

- **Databases**: PostgreSQL 15 and Neo4j 5
- **Data model**: nodes/entities and event-based edges
- **Workload**: analytical query benchmarks (Query 2, 3, 4)
- **Output**: per-run timing CSV files under `results/`

## Repository structure

- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/postgres/`
  - `create_tables.sql`: PostgreSQL schema
  - `queries/`: SQL benchmark queries
  - `indexes/`: index create/drop scripts
- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/neo4j/`
  - `create_schema.cypher`: Neo4j constraints and indexes
  - `queries/`: Cypher benchmark queries
  - `indexes/`: index create/drop scripts
- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/scripts/`
  - data loaders for PostgreSQL and Neo4j
  - benchmark runners for Query 2, 3, 4
- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/results/`
  - benchmark outputs grouped by query
- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/report/`
  - analysis notes

## Prerequisites

- Docker + Docker Compose
- Python 3.10+
- A dataset file at:
  - `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/data.json`

Install Python dependencies:

```bash
cd /home/runner/work/provenance-db-benchmark/provenance-db-benchmark
pip install -r requirements.txt
```

## Start databases

```bash
cd /home/runner/work/provenance-db-benchmark/provenance-db-benchmark
docker-compose up -d
```

Default local endpoints from `docker-compose.yml`:

- PostgreSQL: `localhost:5432` (`postgres` / `4570176501`)
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `localhost:7687` (`neo4j` / `4570176501`)

## Initialize schemas

PostgreSQL:

```bash
docker exec -i dbs_postgres psql -U postgres -d postgres < /home/runner/work/provenance-db-benchmark/provenance-db-benchmark/postgres/create_tables.sql
```

Neo4j:

Open Neo4j Browser at `http://localhost:7474`, then run:

```cypher
:source /home/runner/work/provenance-db-benchmark/provenance-db-benchmark/neo4j/create_schema.cypher
```

## Load data

PostgreSQL loader (CDM18-aware):

```bash
cd /home/runner/work/provenance-db-benchmark/provenance-db-benchmark/scripts
python load_data_postgres_cdm18.py --reset
```

Neo4j loader:

```bash
cd /home/runner/work/provenance-db-benchmark/provenance-db-benchmark/scripts
python load_data_neo4j_cdm18.py --reset
```

Optional connectivity check:

```bash
cd /home/runner/work/provenance-db-benchmark/provenance-db-benchmark/scripts
python test_connection.py
```

## Run benchmarks

From `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/scripts`:

```bash
python benchmark_query2.py --state raw --runs 7
python benchmark_query2.py --state indexed --runs 7

python benchmark_query3.py --state raw --runs 7
python benchmark_query3.py --state indexed --runs 7

python benchmark_query4.py --state raw --runs 7
python benchmark_query4.py --state indexed --runs 7

# Optional: optimized PostgreSQL Query 4 variant
python benchmark_postgres_query4_optimized.py --runs 7
```

Notes:

- `--state` controls output labeling (`raw` or `indexed`) in CSV files.
- Benchmark scripts execute warm-up runs before measured runs.
- Query 4 scripts validate expected row counts.

## Results

Timing CSV files are written to:

- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/results/query2/`
- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/results/query3/`
- `/home/runner/work/provenance-db-benchmark/provenance-db-benchmark/results/query4/`

Each CSV includes:

- `database`
- `state`
- `run`
- `elapsed_ms`
- `row_count`

## Stop databases

```bash
cd /home/runner/work/provenance-db-benchmark/provenance-db-benchmark
docker-compose down
```
