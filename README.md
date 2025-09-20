# Connection Pool Performance Benchmark (PostgreSQL)

This module measures database CRUD performance with and without a connection pool to inform backend choices for high-throughput applications (e.g., crowd density estimation pipelines). It uses a synthetic workload, runs concurrent Create/Read/Update/Delete operations, and compares total time, approximate throughput, and relative latency. Results are printed to the console and saved as a bar chart for easy comparison.

Expected outcome: clear, reproducible performance comparison data for pooled vs non-pooled connections under configurable load.

## What data to feed

Provide environment and configuration, not a dataset:

- A running PostgreSQL instance you can connect to
- A `.env` file with database credentials (see Configuration)
- Optional: monitoring tools to observe resource usage
  - OS-level: top/htop, vmstat, iostat
  - Postgres: pg_stat_activity, pg_stat_statements (if enabled)

The benchmark uses synthetic users and automatically creates a `users` table if it doesn't exist. It inserts unique usernames/emails, reads, updates, and then deletes the same rows during the run so the table is left clean.

Requirements and constraints:
- Network access to PostgreSQL and correct credentials
- Role with permissions to create a table (first run) and perform CRUD
- For larger worker counts, ensure Postgres `max_connections` accommodates the load

## How it works

1. Initialize database and table
   - `setup_database()` checks for table `users`; creates it if missing.
2. Generate N synthetic records
   - Each record has a unique `username` and `email` to avoid constraint collisions.
3. Run CRUD with and without pooling
   - No pool: every operation opens/closes a fresh connection.
   - Pool: shared pool of connections is reused across threads.
   - Concurrency via `ThreadPoolExecutor(max_workers=NUM_WORKERS)`.
4. Measure and compare
   - Wall-clock seconds per phase: create, read, update, delete.
   - Totals are summed and printed; a comparison bar chart is saved.
5. Persist report
   - PNG chart at `task-2/reports/crud_performance_comparison.png`.

Notes on metrics:
- Total time (per phase): sum of elapsed time for each CRUD batch.
- Approx. throughput: operations / elapsed_time.
  - Example: throughput_create ≈ NUM_DATA_POINTS / results['create']
- Approx. avg latency: elapsed_time / operations.
  - Example: latency_create ≈ results['create'] / NUM_DATA_POINTS

## Module overview

Files:
- `db_manager.py`
  - `DB_CONFIG: dict` — populated from environment variables (see `.env`).
  - `BaseDBManager`
    - `get_connection()` / `close_connection(conn)` — abstract.
    - `create_user(username, email) -> int` — returns inserted id.
    - `read_user(user_id) -> tuple|None`
    - `update_user(user_id, new_email) -> None`
    - `delete_user(user_id) -> None`
  - `NoPoolManager(BaseDBManager)` — opens/closes a new connection per call.
  - `PoolManager(BaseDBManager)` — uses `psycopg2.pool.SimpleConnectionPool(1, 50, ...)`.
- `main.py`
  - `setup_database()` — creates table if needed.
  - `run_crud_tests(manager, num_data_points, num_workers) -> dict[str, float]`
    - Returns elapsed seconds per phase: `{create, read, update, delete}`.
  - `generate_report(results_no_pool, results_pool, num_data_points)` — prints totals and saves comparison chart.
  - Entrypoint config: `NUM_DATA_POINTS = 1000`, `NUM_WORKERS = 50` (edit to tune load).

## Quick start

Install dependencies (from repo root):

```bash
pip install -r requirements.txt
```

Create a `.env` file in `task-2/` (see Configuration) and ensure your Postgres server is running and reachable.

Run the benchmark (from repo root or `task-2/`):

```bash
python task-2/main.py
```

Outputs:
- Console summary with total durations and relative gain, e.g.
  - Without Pooling: 12.34s, With Pooling: 5.67s, Performance Gain: 54.05%
- Chart saved to `task-2/reports/crud_performance_comparison.png`
- Detailed per-phase times printed at the end

Use the chart and totals to compare pooled vs non-pooled performance. For deeper analysis, compute throughput/latency with the formulas above and observe system/db metrics during the run.

## Configuration

- Location: `task-2/.env`
- Variables:

```
DB_NAME=<database_name>
USER_NAME=<db_user>
PASSWORD=<db_password>
HOST=<db_host>
PORT=<db_port>
```

- Behavior:
  - Creds are read at import time into `DB_CONFIG`.
  - On first run, the script creates table `users` if missing:
    ```sql
    CREATE TABLE users (
      id SERIAL PRIMARY KEY,
      username VARCHAR(50) UNIQUE NOT NULL,
      email VARCHAR(100) UNIQUE NOT NULL,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    ```
  - Workload size and concurrency are controlled by editing constants in `main.py`:
    - `NUM_DATA_POINTS` (default 1000)
    - `NUM_WORKERS` (default 50)
  - Pool size is set in `PoolManager`: `SimpleConnectionPool(minconn=1, maxconn=50, ...)`.
    - For heavier multi-threaded workloads, consider `ThreadedConnectionPool`.

## Benchmark methodology and considerations

- Tools: built-in threaded load generator and matplotlib reports; optionally pair with OS/DB monitoring.
- Research: consistent benchmarking practices — warm-up runs, stable environment, repeated trials.
- Consider:
  - Throughput: operations per second by phase and overall.
  - Latency: elapsed per operation (approximate averages shown above).
  - Resource usage: CPU, memory, active connections, disk I/O, network.
  - Contention: DB locks, connection saturation (watch Postgres `max_connections`).
  - Client-side concurrency: `NUM_WORKERS` vs pool size; avoid oversubscription if server is small.
  - Pool implementation: this sample uses `SimpleConnectionPool`. For multi-threaded callers, `ThreadedConnectionPool` is often preferred.
  - Variability: run multiple trials and take medians; avoid noisy neighbors on shared hosts.

## Example: customize the load

Edit `task-2/main.py` near the bottom:

```python
NUM_DATA_POINTS = 2000  # total CRUD entities
NUM_WORKERS = 100       # concurrent worker threads
```

Optionally adjust pool size in `task-2/db_manager.py`:

```python
self.pool = psycopg2.pool.SimpleConnectionPool(1, 100, **DB_CONFIG)
```

Re-run the benchmark and compare results and resource usage.

## Troubleshooting

- Connection refused / authentication failed: verify `.env` values and DB reachability.
- Permission denied: ensure the DB user can create tables and perform CRUD in the target schema.
- Connection limit reached: increase Postgres `max_connections` carefully or reduce `NUM_WORKERS`/pool size.
- Missing dependencies: reinstall via `pip install -r requirements.txt`.
- Chart not generated: ensure `matplotlib` is installed and `task-2/reports/` is writable.

## Summary

This benchmark provides an auditable way to compare database performance with vs without connection pooling, focusing on CRUD operations under configurable concurrency. Use the generated totals and chart to quantify speedups and guide production configuration decisions around pooling, worker counts, and database sizing.