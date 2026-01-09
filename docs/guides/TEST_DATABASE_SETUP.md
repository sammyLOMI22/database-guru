# Test Database Setup Guide

**Version**: 1.0
**Last Updated**: December 6, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Prerequisites](#prerequisites)
4. [Docker-Based Databases](#docker-based-databases)
5. [File-Based Databases](#file-based-databases)
6. [Running Tests](#running-tests)
7. [Cleanup](#cleanup)
8. [CI/CD Integration](#cicd-integration)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to set up test databases for connection pooling tests. The test infrastructure supports both Docker-based and file-based databases.

### Test Databases

| Database   | Type   | Port  | Purpose |
|------------|--------|-------|---------|
| PostgreSQL | Docker | 5433  | Async pooling tests |
| MySQL      | Docker | 3307  | Async pooling tests |
| MongoDB    | Docker | 27018 | Future use |
| SQLite     | File   | N/A   | File-based pooling tests |
| DuckDB     | File   | N/A   | File-based pooling tests |

### Sample Data

All databases contain identical sample data:
- **Table**: `products`
- **Columns**: `id`, `name`, `price`, `created_at`
- **Rows**: 100 products ($11.00 - $110.00)
- **Index**: On `price` column

---

## Quick Start

### Option 1: All Databases (Recommended)

```bash
# One-command setup
./scripts/setup_test_databases.sh

# Run all pooling tests
pytest tests/test_connection_pool_manager.py -v
pytest tests/test_pooled_query_execution.py -v
pytest tests/test_pooling_performance.py -v -s -m slow
```

### Option 2: File-Based Only (No Docker)

```bash
# Setup SQLite and DuckDB only
./scripts/setup_test_databases.sh --skip-docker

# Run tests (will skip Docker-based databases)
pytest tests/test_connection_pool_manager.py -v
pytest tests/test_pooled_query_execution.py -v
```

---

## Prerequisites

### Required

- **Python 3.11+** with virtual environment
- **SQLite** (usually pre-installed)
- **Python packages**: asyncpg, aiomysql, aiosqlite, duckdb

### Optional (for Docker-based databases)

- **Docker** and **Docker Compose**
- **netcat** (for health checks)
- **PostgreSQL client tools** (psql)
- **MySQL client tools** (mysql)

### Check Prerequisites

```bash
# Check Python
python --version
# Should be 3.11 or higher

# Check Docker (optional)
docker --version
docker compose version

# Check netcat (optional)
nc -h

# Check database clients (optional)
psql --version
mysql --version
```

### Install Missing Tools

**macOS**:
```bash
brew install docker docker-compose netcat postgresql mysql-client
```

**Ubuntu/Debian**:
```bash
sudo apt-get install docker.io docker-compose netcat postgresql-client mysql-client
```

---

## Docker-Based Databases

### Start All Docker Databases

```bash
# Using setup script (recommended)
./scripts/setup_test_databases.sh

# Or manually
docker compose -f tests/fixtures/docker-compose.test.yml up -d
```

### Verify Containers

```bash
# Check status
docker compose -f tests/fixtures/docker-compose.test.yml ps

# Should show:
# database-guru-postgres-test   running   5433/tcp
# database-guru-mysql-test      running   3307/tcp
# database-guru-mongodb-test    running   27018/tcp
```

### Wait for Health

```bash
# PostgreSQL
./scripts/wait_for_db.sh postgres-test 5433

# MySQL
./scripts/wait_for_db.sh mysql-test 3307

# MongoDB (future use)
./scripts/wait_for_db.sh mongodb-test 27018
```

### Initialize Data

```bash
# Activate virtual environment
source venv/bin/activate

# PostgreSQL
python scripts/init_postgres_test.py

# MySQL
python scripts/init_mysql_test.py
```

### Verify Data

**PostgreSQL**:
```bash
PGPASSWORD=test_pass psql -h localhost -p 5433 -U test_user -d test_pooling -c "SELECT COUNT(*) FROM products;"
# Should return: 100
```

**MySQL**:
```bash
mysql -h 127.0.0.1 -P 3307 -u test_user -ptest_pass -e "SELECT COUNT(*) FROM products;" test_pooling
# Should return: 100
```

---

## File-Based Databases

### SQLite

**Location**: `tests/fixtures/test_pooling.db`

**Initialize**:
```bash
source venv/bin/activate
python scripts/init_sqlite_test.py
```

**Verify**:
```bash
sqlite3 tests/fixtures/test_pooling.db "SELECT COUNT(*) FROM products;"
# Should return: 100
```

**Connection String**:
```
sqlite+aiosqlite:///tests/fixtures/test_pooling.db
```

### DuckDB

**Location**: `tests/fixtures/test_pooling.duckdb`

**Initialize**:
```bash
source venv/bin/activate
python scripts/init_duckdb_test.py
```

**Verify**:
```python
python3 << 'EOF'
import duckdb
conn = duckdb.connect('tests/fixtures/test_pooling.duckdb')
print(conn.execute("SELECT COUNT(*) FROM products").fetchone()[0])
conn.close()
EOF
# Should print: 100
```

**Connection String**:
```
duckdb:///tests/fixtures/test_pooling.duckdb
```

---

## Running Tests

### Unit Tests

```bash
# Connection pool manager tests
pytest tests/test_connection_pool_manager.py -v

# Expected: 18 tests passing
```

### Integration Tests

```bash
# Pooled query execution tests
pytest tests/test_pooled_query_execution.py -v

# Expected: 8 tests passing
```

### Performance Tests

```bash
# Full performance suite (slow)
pytest tests/test_pooling_performance.py -v -s -m slow

# Expected output:
# - Pooling speedup test (4 databases)
# - Concurrent load test
# - Pool exhaustion test
```

**What to expect**:
```
================================ test session starts =================================
tests/test_pooling_performance.py::test_pooling_speedup[PostgreSQL] PASSED
tests/test_pooling_performance.py::test_pooling_speedup[MySQL] PASSED
tests/test_pooling_performance.py::test_pooling_speedup[SQLite] PASSED
tests/test_pooling_performance.py::test_pooling_speedup[DuckDB] PASSED
tests/test_pooling_performance.py::test_concurrent_pooling_performance PASSED
tests/test_pooling_performance.py::test_pool_exhaustion_handling PASSED
================================= 6 passed in 45.23s =================================
```

### Run All Pooling Tests

```bash
# One command for all tests
pytest tests/test_*pool*.py -v

# Or use run_tests.sh
./run_tests.sh tests/test_connection_pool_manager.py
./run_tests.sh tests/test_pooled_query_execution.py
./run_tests.sh tests/test_pooling_performance.py
```

### Test Specific Database

```bash
# Only PostgreSQL tests
pytest tests/test_pooling_performance.py::test_pooling_speedup[PostgreSQL] -v -s

# Only file-based databases
pytest tests/test_pooling_performance.py -v -s -k "SQLite or DuckDB"
```

---

## Cleanup

### Stop Docker Containers

```bash
# Stop containers (keep data)
docker compose -f tests/fixtures/docker-compose.test.yml stop

# Stop and remove containers (keep data)
docker compose -f tests/fixtures/docker-compose.test.yml down

# Stop, remove containers AND volumes (delete all data)
docker compose -f tests/fixtures/docker-compose.test.yml down -v
```

### Remove File-Based Databases

```bash
# Delete local database files
rm -f tests/fixtures/*.db tests/fixtures/*.duckdb

# Files removed:
# - tests/fixtures/test_pooling.db
# - tests/fixtures/test_pooling.duckdb
```

### Complete Cleanup

```bash
# Remove everything
docker compose -f tests/fixtures/docker-compose.test.yml down -v
rm -f tests/fixtures/*.db tests/fixtures/*.duckdb

# Verify cleanup
ls tests/fixtures/
# Should only show: docker-compose.test.yml
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Connection Pooling Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Start test databases
        run: |
          docker compose -f tests/fixtures/docker-compose.test.yml up -d
          sleep 10  # Wait for containers to be ready

      - name: Wait for databases
        run: |
          ./scripts/wait_for_db.sh postgres-test 5433
          ./scripts/wait_for_db.sh mysql-test 3307

      - name: Initialize databases
        run: |
          python scripts/init_postgres_test.py
          python scripts/init_mysql_test.py
          python scripts/init_sqlite_test.py
          python scripts/init_duckdb_test.py

      - name: Run pooling tests
        run: |
          pytest tests/test_connection_pool_manager.py -v
          pytest tests/test_pooled_query_execution.py -v

      - name: Run performance tests
        run: |
          pytest tests/test_pooling_performance.py -v -s -m slow

      - name: Cleanup
        if: always()
        run: |
          docker compose -f tests/fixtures/docker-compose.test.yml down -v
```

### GitLab CI Example

```yaml
test_pooling:
  image: python:3.11
  services:
    - postgres:16-alpine
    - mysql:8.0
  variables:
    POSTGRES_DB: test_pooling
    POSTGRES_USER: test_user
    POSTGRES_PASSWORD: test_pass
    MYSQL_DATABASE: test_pooling
    MYSQL_USER: test_user
    MYSQL_PASSWORD: test_pass
    MYSQL_ROOT_PASSWORD: root_pass
  script:
    - pip install -r requirements.txt
    - python scripts/init_postgres_test.py
    - python scripts/init_mysql_test.py
    - python scripts/init_sqlite_test.py
    - python scripts/init_duckdb_test.py
    - pytest tests/test_*pool*.py -v
```

---

## Troubleshooting

### Docker containers won't start

**Error**: Port already in use

**Solution**:
```bash
# Check what's using the ports
lsof -i :5433  # PostgreSQL
lsof -i :3307  # MySQL
lsof -i :27018 # MongoDB

# Kill the process or change ports in docker-compose.test.yml
```

**Error**: Docker daemon not running

**Solution**:
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### Database initialization fails

**Error**: Connection refused

**Check**:
```bash
# Are containers running?
docker compose -f tests/fixtures/docker-compose.test.yml ps

# Check container logs
docker compose -f tests/fixtures/docker-compose.test.yml logs postgres-test
docker compose -f tests/fixtures/docker-compose.test.yml logs mysql-test
```

**Solution**:
```bash
# Restart containers
docker compose -f tests/fixtures/docker-compose.test.yml restart

# Or recreate
docker compose -f tests/fixtures/docker-compose.test.yml down
docker compose -f tests/fixtures/docker-compose.test.yml up -d
```

### Performance tests skipped

**Message**: `SKIPPED [1] test_pooling_performance.py:XX: PostgreSQL not available`

**Cause**: Database not accessible

**Solution**:
```bash
# For Docker databases
./scripts/setup_test_databases.sh

# For file-based only
./scripts/setup_test_databases.sh --skip-docker

# Verify with:
pytest tests/test_pooling_performance.py -v -s
```

### Tests fail with "table not found"

**Cause**: Database not initialized

**Solution**:
```bash
# Reinitialize all databases
python scripts/init_postgres_test.py
python scripts/init_mysql_test.py
python scripts/init_sqlite_test.py
python scripts/init_duckdb_test.py
```

### Health check script fails

**Error**: `nc: command not found`

**Solution**:
```bash
# Install netcat
brew install netcat        # macOS
sudo apt install netcat    # Ubuntu/Debian

# Or skip health checks
# Edit setup_test_databases.sh to not use netcat
```

---

## Database Connection Details

### PostgreSQL Test Database

```
Host: localhost
Port: 5433
Database: test_pooling
User: test_user
Password: test_pass

Connection String:
  postgresql://test_user:test_pass@localhost:5433/test_pooling
  postgresql+asyncpg://test_user:test_pass@localhost:5433/test_pooling

Docker Container:
  database-guru-postgres-test

psql Command:
  PGPASSWORD=test_pass psql -h localhost -p 5433 -U test_user -d test_pooling
```

### MySQL Test Database

```
Host: 127.0.0.1 (not localhost!)
Port: 3307
Database: test_pooling
User: test_user
Password: test_pass
Root Password: root_pass

Connection String:
  mysql://test_user:test_pass@localhost:3307/test_pooling
  mysql+aiomysql://test_user:test_pass@localhost:3307/test_pooling

Docker Container:
  database-guru-mysql-test

mysql Command:
  mysql -h 127.0.0.1 -P 3307 -u test_user -ptest_pass test_pooling
```

### MongoDB Test Database

```
Host: localhost
Port: 27018
Database: test_pooling
(No authentication for test environment)

Connection String:
  mongodb://localhost:27018/test_pooling

Docker Container:
  database-guru-mongodb-test

mongosh Command:
  mongosh --host localhost --port 27018 test_pooling

Status: Container ready, awaiting MongoDB query implementation
```

### SQLite Test Database

```
Path: tests/fixtures/test_pooling.db
(No host/port/authentication)

Connection String:
  sqlite:///tests/fixtures/test_pooling.db
  sqlite+aiosqlite:///tests/fixtures/test_pooling.db

sqlite3 Command:
  sqlite3 tests/fixtures/test_pooling.db
```

### DuckDB Test Database

```
Path: tests/fixtures/test_pooling.duckdb
(No host/port/authentication)

Connection String:
  duckdb:///tests/fixtures/test_pooling.duckdb

Python Access:
  import duckdb
  conn = duckdb.connect('tests/fixtures/test_pooling.duckdb')
```

---

## Test Data Schema

All databases use this identical schema:

```sql
-- Products table
CREATE TABLE products (
    id INTEGER/SERIAL PRIMARY KEY,        -- Auto-increment ID
    name VARCHAR(255)/TEXT NOT NULL,      -- Product name
    price DECIMAL(10,2)/REAL/DOUBLE,      -- Price
    created_at TIMESTAMP DEFAULT NOW()     -- Creation timestamp
);

-- Index for performance
CREATE INDEX idx_products_price ON products(price);

-- 100 rows of sample data
-- "Product 1" ($11.00) through "Product 100" ($110.00)
```

### Query Examples

```sql
-- Count all products
SELECT COUNT(*) FROM products;
-- Returns: 100

-- Get first 5 products
SELECT id, name, price FROM products LIMIT 5;
-- Returns:
--   1 | Product 1  | 11.00
--   2 | Product 2  | 12.00
--   3 | Product 3  | 13.00
--   4 | Product 4  | 14.00
--   5 | Product 5  | 15.00

-- Find products over $50
SELECT COUNT(*) FROM products WHERE price > 50;
-- Returns: 50

-- Average price
SELECT AVG(price) FROM products;
-- Returns: 60.50
```

---

## See Also

- [Connection Pooling Guide](./CONNECTION_POOLING_GUIDE.md) - User guide for connection pooling
- [Implementation Plan](../planning/CONNECTION_POOLING_IMPLEMENTATION_PLAN.md) - Development details
- [Architecture (CLAUDE.md)](../../CLAUDE.md) - System architecture

---

**Last Updated**: December 6, 2025
**Version**: 1.0
