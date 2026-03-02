# NoSQL Sample Databases Guide

Set up and query five NoSQL databases — MongoDB, Redis, Cassandra, DynamoDB, and Elasticsearch — pre-loaded with e-commerce sample data to test Database Guru's NoSQL support.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ with pip
- Database Guru backend running on port 8000

## Quick Start

```bash
# 1. Install seed script dependencies
pip install -r requirements-nosql-seed.txt

# 2. Start all NoSQL services and seed them with data
./scripts/start_nosql.sh
```

That's it. Five databases are now running and populated. Register them in Database Guru and start querying.

## What Gets Installed

### Services

| Service | Image | Port | Data |
|---------|-------|------|------|
| MongoDB | mongo:7 | 27017 | 4 collections + activity log |
| Redis | redis:7-alpine | 6380 | Hashes, sets, sorted sets + sessions |
| Cassandra | cassandra:4 | 9042 | 4 tables + time-series sensor data |
| DynamoDB Local | amazon/dynamodb-local | 8001 | 4 tables with composite keys |
| Elasticsearch | elasticsearch:8.12.0 | 9200 | 5 indices + server logs |

### Sample Data

All databases share the same e-commerce dataset (matching the SQL sample in `scripts/create_sample_db.py`):

- **15 customers** — names, emails, cities across US states
- **20 products** — in 4 categories (Electronics, Accessories, Office, Furniture)
- **50 orders** — with line items, statuses, dates
- **~30 reviews** — ratings 1-5 with comments

Each database also gets extras that showcase its strengths (see per-database sections below).

## Registering Connections in Database Guru

After seeding, register each database through the UI or API.

### Via the UI

Open Database Guru, click **+ Add Connection**, and fill in:

#### MongoDB
| Field | Value |
|-------|-------|
| Name | `mongo-sample` |
| Type | `MongoDB` |
| Host | `localhost` |
| Port | `27017` |
| Database | `ecommerce` |

#### Redis
| Field | Value |
|-------|-------|
| Name | `redis-sample` |
| Type | `Redis` |
| Host | `localhost` |
| Port | `6380` |
| Database | `0` |

#### Cassandra
| Field | Value |
|-------|-------|
| Name | `cassandra-sample` |
| Type | `Cassandra` |
| Host | `localhost` |
| Port | `9042` |
| Database | `ecommerce` |

#### DynamoDB Local
| Field | Value |
|-------|-------|
| Name | `dynamodb-sample` |
| Type | `DynamoDB` |
| Host (Region) | `us-east-1` |
| Username (Access Key) | `fakeAccessKeyId` |
| Password (Secret Key) | `fakeSecretAccessKey` |

> **Note:** DynamoDB Local also requires `DYNAMODB_ENDPOINT=http://localhost:8001` in your `.env` file so the backend connects to the local emulator instead of AWS.

#### Elasticsearch
| Field | Value |
|-------|-------|
| Name | `elasticsearch-sample` |
| Type | `Elasticsearch` |
| Host | `localhost` |
| Port | `9200` |

No authentication is required for local Elasticsearch.

### Via the API

```bash
# MongoDB
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"mongo-sample","database_type":"mongodb","host":"localhost","port":27017,"database_name":"ecommerce"}'

# Redis
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"redis-sample","database_type":"redis","host":"localhost","port":6380,"database_name":"0"}'

# Cassandra
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"cassandra-sample","database_type":"cassandra","host":"localhost","port":9042,"database_name":"ecommerce"}'

# DynamoDB Local
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"dynamodb-sample","database_type":"dynamodb","host":"us-east-1","username":"fakeAccessKeyId","password":"fakeSecretAccessKey"}'

# Elasticsearch
curl -X POST http://localhost:8000/api/connections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"elasticsearch-sample","database_type":"elasticsearch","host":"localhost","port":9200}'
```

## Example Queries by Database

Once connected, try these natural language queries in Database Guru.

### MongoDB

MongoDB stores data in the `ecommerce` database with collections: `customers`, `products`, `orders`, `reviews`, `activity_log`.

Orders use **embedded documents** — each order contains its line items as a nested array, a classic MongoDB pattern.

| Try asking... | What it tests |
|---------------|---------------|
| "Show all products in the Electronics category" | Simple find with filter |
| "What is the average order total?" | Aggregation pipeline |
| "List customers from California" | Filter on nested field |
| "Show the top 5 most expensive orders with customer names" | Lookup (join) + sort + limit |
| "How many orders does each customer have?" | Group + count aggregation |
| "Show recent activity log entries for mobile devices" | Query on DB-specific collection |
| "What products were most viewed in the activity log?" | Aggregation on nested metadata |

**Schema highlights:**
- `orders.items` — array of embedded documents (product_id, quantity, unit_price, line_total)
- `activity_log.metadata` — polymorphic nested object (varies by action type)
- Indexes on: `customers.email` (unique), `customers.state`, `products.category`, `orders.customer_id`, `orders.status`

### Redis

Redis stores data in database 0 with these key patterns:

| Key Pattern | Type | Contents |
|-------------|------|----------|
| `customer:{id}` | Hash | name, email, city, state |
| `product:{id}` | Hash | name, category, price, stock |
| `order:{id}` | Hash | customer_id, status, total_amount, order_date |
| `top_products` | Sorted Set | Product names scored by price |
| `category:{name}` | Set | Product IDs in that category |
| `customer:{id}:orders` | Set | Order IDs for that customer |
| `session:{id}` | String (JSON) | Cart data with 1h TTL |
| `cache:product_detail:{id}` | String (JSON) | Cached product detail with 5m TTL |
| `rate_limit:api:{id}` | String (counter) | API rate limit with 60s TTL |

| Try asking... | What it tests |
|---------------|---------------|
| "What are the top 5 most expensive products?" | ZREVRANGE on sorted set |
| "Show customer 3's details" | HGETALL on hash |
| "How many products are in the Electronics category?" | SCARD on set |
| "List all active sessions" | KEYS + GET on session:* |
| "What orders belong to customer 1?" | SMEMBERS on customer:1:orders |
| "Show all product categories" | KEYS pattern matching |

### Cassandra

Cassandra uses the `ecommerce` keyspace with tables designed around query patterns (partition keys matter):

| Table | Partition Key | Clustering Key | Rows |
|-------|--------------|----------------|------|
| `customers_by_id` | customer_id | — | 15 |
| `products_by_category` | category | product_id | 20 |
| `orders_by_customer` | customer_id | order_date DESC, order_id | 50 |
| `reviews_by_product` | product_id | review_id | ~30 |
| `sensor_readings` | (sensor_id, reading_date) | reading_time DESC | 504 |

| Try asking... | What it tests |
|---------------|---------------|
| "Show all orders for customer 3" | Partition key query |
| "List all products in the Office category" | Partition key query |
| "What are the latest sensor readings for sensor-001?" | Compound partition + clustering |
| "Show the average rating for product 5" | Aggregation within partition |
| "Find all customers from Texas" | Full table scan (ALLOW FILTERING) |
| "Show temperature readings for sensor-002 on a specific date" | Compound partition key query |

**Important:** Cassandra queries work best when filtering by partition key. Queries that require scanning all partitions may need `ALLOW FILTERING` and the LLM should generate this appropriately.

### DynamoDB

DynamoDB has four tables:

| Table | Partition Key | Sort Key | Items |
|-------|--------------|----------|-------|
| `Products` | product_id (N) | — | 20 |
| `Orders` | customer_id (N) | order_id (N) | 50 |
| `Customers` | customer_id (N) | — | 15 |
| `Sessions` | session_id (S) | — | 20 (with TTL) |

| Try asking... | What it tests |
|---------------|---------------|
| "List all products with stock less than 50" | Scan with filter |
| "Show orders for customer 7" | Query on partition key |
| "What is the most expensive product?" | Scan + sort |
| "Show all active sessions" | Scan on Sessions table |
| "Find customers in California" | Scan with filter expression |
| "How many orders has customer 1 placed?" | Query + count |

**Note:** DynamoDB generates PartiQL queries. Queries on partition keys are efficient; queries requiring scans are slower but still work.

### Elasticsearch

Elasticsearch has five indices:

| Index | Documents | Good for |
|-------|-----------|----------|
| `products` | 20 | Full-text search, keyword filters |
| `customers` | 15 | Keyword search, state aggregations |
| `orders` | 50 | Date range queries, status aggregations |
| `reviews` | ~30 | Full-text comment search, rating stats |
| `server_logs` | 500 | Time-series, log level aggregations |

| Try asking... | What it tests |
|---------------|---------------|
| "Search for products matching 'wireless'" | Full-text search |
| "Show all ERROR logs from payment-service" | Multi-field filter |
| "What is the average response time by service?" | Terms + avg aggregation |
| "Find orders placed in the last 30 days" | Date range query |
| "Show the distribution of log levels" | Terms aggregation |
| "Find reviews mentioning 'recommend'" | Full-text search on comments |
| "What are the top 5 services by error count?" | Terms + filter aggregation |
| "Show log entries with response time over 1000ms" | Range query |

**Schema highlights:**
- `products.name` is mapped as both `text` (for search) and `keyword` (for exact match)
- `server_logs` has 500 entries over 7 days with levels (INFO 60%, WARN 20%, ERROR 10%, DEBUG 10%)
- Date fields (`order_date`, `timestamp`) are mapped as `date` type for range queries

## Script Reference

### start_nosql.sh

```bash
./scripts/start_nosql.sh                    # Start all services + seed all databases
./scripts/start_nosql.sh --no-seed          # Start services only
./scripts/start_nosql.sh --db=mongodb,redis # Start all services, seed only MongoDB + Redis
./scripts/start_nosql.sh --clean            # Drop existing data before seeding
```

### stop_nosql.sh

```bash
./scripts/stop_nosql.sh      # Stop containers (data preserved in Docker volumes)
./scripts/stop_nosql.sh -v   # Stop containers and delete all data volumes
```

### seed_nosql_data.py

Run the seed script directly for more control:

```bash
# Seed all databases
python scripts/seed_nosql_data.py

# Seed specific databases
python scripts/seed_nosql_data.py --db mongodb,elasticsearch

# Clean and re-seed
python scripts/seed_nosql_data.py --db cassandra --clean

# Custom host/port
python scripts/seed_nosql_data.py --db redis --redis-host 192.168.1.10 --redis-port 6379
```

Available host/port overrides:

| Flag | Default |
|------|---------|
| `--mongo-host` / `--mongo-port` | localhost:27017 |
| `--redis-host` / `--redis-port` | localhost:6380 |
| `--cassandra-host` / `--cassandra-port` | localhost:9042 |
| `--dynamodb-host` / `--dynamodb-port` | localhost:8001 |
| `--es-host` / `--es-port` | localhost:9200 |

The script is idempotent — running it again skips collections/tables that already have data. Use `--clean` to force a fresh load.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cassandra takes a long time to start | Normal — Cassandra needs 60-90s for initial startup. The start script waits up to 120s. |
| `pymongo not installed` (or similar) | Run `pip install -r requirements-nosql-seed.txt` |
| Port already in use | Check for conflicting services. Redis uses 6380 (not 6379) to avoid conflict with the production Redis in docker-compose.yml. DynamoDB uses 8001 (not 8000) to avoid conflict with the backend. |
| DynamoDB queries fail in Database Guru | Add `DYNAMODB_ENDPOINT=http://localhost:8001` to your `.env` file |
| Elasticsearch cluster health is yellow | Expected for single-node setup — replicas can't be assigned. Queries still work fine. |
| Connection test fails after seeding | Make sure the backend can reach `localhost` ports. If running the backend in Docker, use `host.docker.internal` instead of `localhost`. |
| Seed script skips data ("already exists") | Data from a previous run is still present. Use `--clean` to drop and recreate. |

## Cleanup

To remove everything:

```bash
# Stop containers and delete all data
./scripts/stop_nosql.sh -v

# Optionally remove the seed dependencies
pip uninstall pymongo redis cassandra-driver boto3 elasticsearch
```
