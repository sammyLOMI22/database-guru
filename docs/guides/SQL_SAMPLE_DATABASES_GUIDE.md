# SQL Sample Databases Guide

Set up and query four SQL databases — PostgreSQL, MySQL, SQLite, and DuckDB — pre-loaded with e-commerce sample data to test Database Guru's SQL support.

## Prerequisites

- Docker and Docker Compose installed (for PostgreSQL and MySQL)
- Python 3.11+ with pip
- Database Guru backend running on port 8000

## Quick Start

```bash
# 1. Install seed script dependencies
pip install -r requirements-sql-seed.txt

# 2. Start PostgreSQL + MySQL and seed all 4 databases
./scripts/start_sql.sh
```

That's it. PostgreSQL and MySQL are running in Docker, SQLite and DuckDB files are created in the project root. Register them in Database Guru and start querying.

## What Gets Installed

### Services

| Database | Type | Location | Data |
|----------|------|----------|------|
| PostgreSQL | Docker (postgres:16-alpine) | localhost:5433 | 8 tables |
| MySQL | Docker (mysql:8.0) | localhost:3307 | 8 tables |
| SQLite | File | sample_ecommerce.db | 6 tables + FTS5 index |
| DuckDB | File | sample_ecommerce.duckdb | 8 tables |

### Sample Data

All databases share the same e-commerce dataset (matching the NoSQL sample in `scripts/seed_nosql_data.py`):

- **15 customers** — names, emails, cities across US states
- **4 categories** — Electronics, Accessories, Office, Furniture
- **20 products** — with category foreign keys and stock quantities
- **50 orders** — with statuses, dates, and shipped dates
- **~130 order items** — line items linking orders to products
- **~30 reviews** — ratings 1-5 with comments

Each database also gets extras that showcase its strengths (see per-database sections below).

## Registering Connections in Database Guru

After seeding, register each database through the UI or API.

### Via the UI

Open Database Guru, click **+ Add Connection**, and fill in:

#### PostgreSQL
| Field | Value |
|-------|-------|
| Name | `postgresql-sample` |
| Type | `PostgreSQL` |
| Host | `localhost` |
| Port | `5433` |
| Database | `ecommerce` |
| Username | `dbguru` |
| Password | `dbguru` |

#### MySQL
| Field | Value |
|-------|-------|
| Name | `mysql-sample` |
| Type | `MySQL` |
| Host | `localhost` |
| Port | `3307` |
| Database | `ecommerce` |
| Username | `dbguru` |
| Password | `dbguru` |

#### SQLite
| Field | Value |
|-------|-------|
| Name | `sqlite-sample` |
| Type | `SQLite` |
| Database Path | `sample_ecommerce.db` |

#### DuckDB
| Field | Value |
|-------|-------|
| Name | `duckdb-sample` |
| Type | `DuckDB` |
| Database Path | `sample_ecommerce.duckdb` |

### Via the API

```bash
# PostgreSQL
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"postgresql-sample","database_type":"postgresql","host":"localhost","port":5433,"database_name":"ecommerce","username":"dbguru","password":"dbguru"}'

# MySQL
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"mysql-sample","database_type":"mysql","host":"localhost","port":3307,"database_name":"ecommerce","username":"dbguru","password":"dbguru"}'

# SQLite
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"sqlite-sample","database_type":"sqlite","database_name":"sample_ecommerce.db"}'

# DuckDB
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"duckdb-sample","database_type":"duckdb","database_name":"sample_ecommerce.duckdb"}'
```

## Database Schemas

### Core Tables (all 4 databases)

```
customers          categories         products
├─ customer_id PK  ├─ category_id PK  ├─ product_id PK
├─ name            ├─ name            ├─ name
├─ email (unique)  └─ description     ├─ category_id FK → categories
├─ city                               ├─ price
├─ state                              ├─ stock_quantity
└─ created_at                         └─ created_at

orders                    order_items               reviews
├─ order_id PK            ├─ order_item_id PK       ├─ review_id PK
├─ customer_id FK         ├─ order_id FK → orders   ├─ product_id FK → products
├─ total_amount           ├─ product_id FK          ├─ customer_id FK → customers
├─ status                 ├─ quantity               ├─ rating (1-5)
├─ order_date             └─ unit_price             ├─ comment
└─ shipped_date                                     └─ created_at
```

### DB-Specific Extras

Each database includes additional tables that showcase its unique capabilities.

## Example Queries by Database

### PostgreSQL

**Core tables** plus two extras:

| Extra Table | Rows | Purpose |
|-------------|------|---------|
| `employee_hierarchy` | 12 | Recursive CTE demo (self-referencing manager_id) |
| `audit_log` | 50 | JSONB column demo (old_values, new_values as JSONB) |

| Try asking... | What it tests |
|---------------|---------------|
| "What are the top 5 best-selling products?" | JOIN + GROUP BY + ORDER BY |
| "Show me all orders from customers in California" | Multi-table JOIN with filter |
| "What's the average order value by status?" | GROUP BY with aggregate |
| "Show the total revenue by product category" | Multi-level JOIN + SUM |
| "Show the full management chain for each employee" | Recursive CTE |
| "Who reports to Bob Martinez, directly or indirectly?" | Recursive CTE with filter |
| "Show recent audit log changes to the orders table" | JSONB column query |
| "Which products have the highest average rating?" | JOIN + AVG + ORDER BY |

**Schema highlights:**
- `employee_hierarchy.manager_id` — self-referencing FK, ideal for `WITH RECURSIVE` queries
- `audit_log.old_values` / `audit_log.new_values` — JSONB columns, queryable with `->`, `->>`, `@>` operators
- Full foreign key constraints on all tables

### MySQL

**Core tables** plus two extras:

| Extra Table | Rows | Purpose |
|-------------|------|---------|
| `product_inventory_log` | 80 | Timestamp tracking (restock, sale, return, etc.) |
| `customer_preferences` | 15 | JSON column demo (nested preferences object) |

| Try asking... | What it tests |
|---------------|---------------|
| "What are the top 5 best-selling products?" | JOIN + GROUP BY + ORDER BY |
| "Show total revenue per month" | DATE functions + GROUP BY |
| "Which customers prefer dark theme?" | JSON_EXTRACT on preferences |
| "Show customers who prefer email notifications" | JSON nested path query |
| "What are the most common inventory change types?" | GROUP BY + COUNT |
| "Show recent restocks for product 5" | Filter + ORDER BY timestamp |
| "Which products are running low on stock?" | Simple filter + ORDER BY |
| "List all customers with their favorite categories" | JSON array extraction |

**Schema highlights:**
- `customer_preferences.preferences` — JSON column with nested structure: `{"theme": "dark", "notifications": {"email": true}, "favorite_categories": [...]}`
- `product_inventory_log` — tracks stock changes with change_type, quantity_change, reason
- InnoDB engine with utf8mb4 charset on all tables

### SQLite

**Core tables** plus one extra:

| Extra | Type | Purpose |
|-------|------|---------|
| `product_search` | FTS5 virtual table | Full-text search over product names and categories |

| Try asking... | What it tests |
|---------------|---------------|
| "What are the top 5 best-selling products?" | JOIN + GROUP BY + ORDER BY |
| "Show me customers who haven't placed any orders" | LEFT JOIN + IS NULL |
| "What's the total revenue by category?" | Multi-table JOIN + SUM |
| "How many orders were shipped last month?" | Date filtering + COUNT |
| "Which products have the highest ratings?" | JOIN + AVG + ORDER BY |
| "Show me products low in stock" | Simple filter + ORDER BY |
| "What products are in the Office category?" | JOIN with filter |
| "Show me customers from Texas with their order count" | JOIN + GROUP BY + HAVING |

**Schema highlights:**
- `product_search` — FTS5 virtual table for full-text search (supports MATCH queries)
- Indexes on: customers.state, products.category_id, orders.customer_id, orders.status
- Standard SQLite types (TEXT, REAL, INTEGER, DATETIME)

### DuckDB

**Core tables** plus two extras:

| Extra Table | Rows | Purpose |
|-------------|------|---------|
| `sales_analytics` | ~130 | Denormalized OLAP view (pre-joined orders + customers + products) |
| `monthly_summary` | ~3 | Pre-aggregated monthly revenue, orders, customers |

| Try asking... | What it tests |
|---------------|---------------|
| "Show monthly revenue trends" | Query on pre-aggregated data |
| "What is the total revenue by category and month?" | GROUP BY on sales_analytics |
| "Who are the top spending customers?" | Aggregate + ORDER BY |
| "What day of the week has the most orders?" | EXTRACT + GROUP BY on analytics |
| "Show the average order value by customer state" | Multi-column GROUP BY |
| "Compare revenue between Electronics and Furniture" | Filter + aggregate |
| "What's the month-over-month growth in orders?" | Window functions / LAG |
| "Show the distribution of order values" | Histogram-style query |

**Schema highlights:**
- `sales_analytics` — fully denormalized join of orders, customers, products, categories with extracted date parts (year, month, day_of_week)
- `monthly_summary` — pre-computed monthly KPIs (total_orders, unique_customers, total_revenue, avg_line_total, total_items_sold)
- DuckDB excels at analytical queries — window functions, EXTRACT, complex aggregations

## Cross-Database Queries

Since all 4 databases share the same core schema and data, you can ask the same question against different connections to compare SQL dialect generation:

| Question | Tests across dialects |
|----------|----------------------|
| "What are the top 5 best-selling products?" | JOIN + GROUP BY + LIMIT syntax |
| "Show orders from the last 30 days" | Date function differences |
| "What's the average rating per product category?" | Multi-table JOIN + aggregate |
| "Show customers who spent more than $500 total" | HAVING clause |
| "Which products have never been ordered?" | LEFT JOIN + IS NULL vs NOT EXISTS |

This is useful for verifying Database Guru generates correct SQL for each dialect.

## Script Reference

### start_sql.sh

```bash
./scripts/start_sql.sh                          # Start Docker DBs + seed all 4
./scripts/start_sql.sh --no-seed                # Start Docker services only
./scripts/start_sql.sh --db=postgresql,sqlite    # Start all, seed only PostgreSQL + SQLite
./scripts/start_sql.sh --clean                   # Drop existing data before seeding
```

### stop_sql.sh

```bash
./scripts/stop_sql.sh      # Stop Docker containers (data preserved in volumes)
./scripts/stop_sql.sh -v   # Stop containers and delete all data volumes
```

Note: SQLite and DuckDB files (`sample_ecommerce.db`, `sample_ecommerce.duckdb`) are not affected by stop_sql.sh. Delete them manually if needed.

### seed_sql_data.py

Run the seed script directly for more control:

```bash
# Seed all databases
python scripts/seed_sql_data.py

# Seed specific databases
python scripts/seed_sql_data.py --db postgresql,duckdb

# Clean and re-seed MySQL
python scripts/seed_sql_data.py --db mysql --clean

# Custom host/port for PostgreSQL
python scripts/seed_sql_data.py --db postgresql --pg-host 192.168.1.10 --pg-port 5432

# Custom file path for SQLite
python scripts/seed_sql_data.py --db sqlite --sqlite-path /tmp/test.db
```

Available overrides:

| Flag | Default |
|------|---------|
| `--pg-host` / `--pg-port` | localhost:5433 |
| `--mysql-host` / `--mysql-port` | localhost:3307 |
| `--sqlite-path` | sample_ecommerce.db |
| `--duckdb-path` | sample_ecommerce.duckdb |

The script is idempotent — running it again skips databases that already have data. Use `--clean` to force a fresh load.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MySQL takes a long time to start | Normal — MySQL 8.0 needs 20-30s for initialization. The start script waits up to 60s. |
| `psycopg2 not installed` (or similar) | Run `pip install -r requirements-sql-seed.txt` |
| Port 5433 already in use | The test docker-compose (`tests/fixtures/docker-compose.test.yml`) also uses 5433. Stop it first: `docker compose -f tests/fixtures/docker-compose.test.yml down` |
| Port 3307 already in use | Same — check for the test MySQL container. |
| PostgreSQL "FATAL: role dbguru does not exist" | The Docker container creates the role on first start. If volumes were created by a different config, run `./scripts/stop_sql.sh -v` and start fresh. |
| SQLite "database is locked" | Make sure no other process has the file open. The backend and seed script shouldn't run simultaneously on the same file. |
| DuckDB import error | Run `pip install duckdb>=0.10` — DuckDB requires a pip install (not in stdlib). |
| Connection test fails in Database Guru | If running the backend in Docker, use `host.docker.internal` instead of `localhost` for PostgreSQL/MySQL. |

## Cleanup

```bash
# Stop Docker containers and delete all data
./scripts/stop_sql.sh -v

# Delete file-based databases
rm -f sample_ecommerce.db sample_ecommerce.duckdb

# Optionally remove seed dependencies
pip uninstall psycopg2-binary pymysql duckdb
```
