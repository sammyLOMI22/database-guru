#!/usr/bin/env python3
"""
Seed NoSQL databases with sample e-commerce data for testing Database Guru.

Usage:
    python scripts/seed_nosql_data.py                    # Seed all databases
    python scripts/seed_nosql_data.py --db mongodb,redis  # Seed specific databases
    python scripts/seed_nosql_data.py --clean             # Drop and recreate before seeding
    python scripts/seed_nosql_data.py --db mongodb --clean --mongo-host myhost

Requires: pip install -r requirements-nosql-seed.txt
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# ---------------------------------------------------------------------------
# Shared sample data (mirrors scripts/create_sample_db.py)
# ---------------------------------------------------------------------------

CUSTOMERS = [
    {"id": 1, "name": "John Doe", "email": "john.doe@email.com", "city": "New York", "state": "NY"},
    {"id": 2, "name": "Jane Smith", "email": "jane.smith@email.com", "city": "Los Angeles", "state": "CA"},
    {"id": 3, "name": "Mike Johnson", "email": "mike.j@email.com", "city": "Chicago", "state": "IL"},
    {"id": 4, "name": "Sarah Williams", "email": "sarah.w@email.com", "city": "Houston", "state": "TX"},
    {"id": 5, "name": "David Brown", "email": "david.brown@email.com", "city": "Phoenix", "state": "AZ"},
    {"id": 6, "name": "Emily Davis", "email": "emily.d@email.com", "city": "Philadelphia", "state": "PA"},
    {"id": 7, "name": "Chris Wilson", "email": "chris.wilson@email.com", "city": "San Antonio", "state": "TX"},
    {"id": 8, "name": "Lisa Anderson", "email": "lisa.a@email.com", "city": "San Diego", "state": "CA"},
    {"id": 9, "name": "Tom Martinez", "email": "tom.m@email.com", "city": "Dallas", "state": "TX"},
    {"id": 10, "name": "Amy Taylor", "email": "amy.taylor@email.com", "city": "San Jose", "state": "CA"},
    {"id": 11, "name": "Robert Lee", "email": "robert.lee@email.com", "city": "Austin", "state": "TX"},
    {"id": 12, "name": "Jessica White", "email": "jessica.w@email.com", "city": "Jacksonville", "state": "FL"},
    {"id": 13, "name": "James Harris", "email": "james.h@email.com", "city": "San Francisco", "state": "CA"},
    {"id": 14, "name": "Linda Clark", "email": "linda.c@email.com", "city": "Columbus", "state": "OH"},
    {"id": 15, "name": "Michael Lewis", "email": "michael.l@email.com", "city": "Fort Worth", "state": "TX"},
]

PRODUCTS = [
    {"id": 1, "name": "Laptop Pro 15", "category": "Electronics", "price": 1299.99, "stock": 45},
    {"id": 2, "name": "Wireless Mouse", "category": "Electronics", "price": 29.99, "stock": 150},
    {"id": 3, "name": "USB-C Cable", "category": "Accessories", "price": 12.99, "stock": 200},
    {"id": 4, "name": "Mechanical Keyboard", "category": "Electronics", "price": 149.99, "stock": 75},
    {"id": 5, "name": "Monitor 27 inch", "category": "Electronics", "price": 399.99, "stock": 30},
    {"id": 6, "name": "Webcam HD", "category": "Electronics", "price": 79.99, "stock": 60},
    {"id": 7, "name": "Desk Lamp", "category": "Office", "price": 34.99, "stock": 100},
    {"id": 8, "name": "Office Chair", "category": "Furniture", "price": 249.99, "stock": 25},
    {"id": 9, "name": "Standing Desk", "category": "Furniture", "price": 499.99, "stock": 15},
    {"id": 10, "name": "Notebook Set", "category": "Office", "price": 15.99, "stock": 300},
    {"id": 11, "name": "Pen Pack", "category": "Office", "price": 8.99, "stock": 400},
    {"id": 12, "name": "Backpack", "category": "Accessories", "price": 59.99, "stock": 80},
    {"id": 13, "name": "Water Bottle", "category": "Accessories", "price": 19.99, "stock": 150},
    {"id": 14, "name": "Coffee Mug", "category": "Accessories", "price": 12.99, "stock": 200},
    {"id": 15, "name": "Headphones", "category": "Electronics", "price": 199.99, "stock": 50},
    {"id": 16, "name": "Phone Case", "category": "Accessories", "price": 24.99, "stock": 180},
    {"id": 17, "name": "Screen Protector", "category": "Accessories", "price": 9.99, "stock": 250},
    {"id": 18, "name": "Charging Pad", "category": "Electronics", "price": 39.99, "stock": 90},
    {"id": 19, "name": "Bluetooth Speaker", "category": "Electronics", "price": 89.99, "stock": 65},
    {"id": 20, "name": "Tablet 10 inch", "category": "Electronics", "price": 449.99, "stock": 40},
]

ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]

REVIEW_COMMENTS = [
    "Great product, highly recommend!",
    "Good quality for the price.",
    "Not as expected, disappointed.",
    "Amazing! Exactly what I needed.",
    "Decent product, works well.",
    "Poor quality, would not buy again.",
    "Excellent value for money!",
    "Just okay, nothing special.",
    "Love it! Will buy again.",
    "Terrible experience, avoid.",
]

random.seed(42)  # Reproducible data


def generate_orders(num_orders=50):
    """Generate order data with embedded line items."""
    orders = []
    base_date = datetime.now(timezone.utc) - timedelta(days=90)
    for i in range(1, num_orders + 1):
        customer_id = random.randint(1, len(CUSTOMERS))
        status = random.choice(ORDER_STATUSES)
        order_date = base_date + timedelta(days=random.randint(0, 90))
        shipped_date = None
        if status in ("shipped", "delivered"):
            shipped_date = order_date + timedelta(days=random.randint(1, 5))

        items = []
        total = 0.0
        for _ in range(random.randint(1, 4)):
            product = random.choice(PRODUCTS)
            qty = random.randint(1, 3)
            line_total = round(product["price"] * qty, 2)
            total += line_total
            items.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": qty,
                "unit_price": product["price"],
                "line_total": line_total,
            })

        orders.append({
            "id": i,
            "customer_id": customer_id,
            "status": status,
            "total_amount": round(total, 2),
            "order_date": order_date.isoformat(),
            "shipped_date": shipped_date.isoformat() if shipped_date else None,
            "items": items,
        })
    return orders


def generate_reviews(num_reviews=30):
    """Generate review data."""
    reviews = []
    seen = set()
    for i in range(1, num_reviews + 1):
        product_id = random.randint(1, len(PRODUCTS))
        customer_id = random.randint(1, len(CUSTOMERS))
        key = (product_id, customer_id)
        if key in seen:
            continue
        seen.add(key)
        reviews.append({
            "id": i,
            "product_id": product_id,
            "customer_id": customer_id,
            "rating": random.randint(1, 5),
            "comment": random.choice(REVIEW_COMMENTS),
            "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 60))).isoformat(),
        })
    return reviews


ORDERS = generate_orders()
REVIEWS = generate_reviews()


# ===========================================================================
# MongoDB
# ===========================================================================

def seed_mongodb(host="localhost", port=27017, clean=False):
    """Seed MongoDB with e-commerce data + activity log."""
    try:
        from pymongo import MongoClient
    except ImportError:
        print("  SKIP pymongo not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  MongoDB  ({host}:{port})")
    print(f"{'='*60}")

    client = MongoClient(host, port, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    db = client["ecommerce"]

    if clean:
        client.drop_database("ecommerce")
        print("  Dropped existing 'ecommerce' database")

    # Customers
    if db.customers.count_documents({}) == 0:
        db.customers.insert_many([{**c, "_id": c["id"]} for c in CUSTOMERS])
        print(f"  Inserted {len(CUSTOMERS)} customers")
    else:
        print(f"  Customers already exist ({db.customers.count_documents({})} docs), skipping")

    # Products
    if db.products.count_documents({}) == 0:
        db.products.insert_many([{**p, "_id": p["id"]} for p in PRODUCTS])
        print(f"  Inserted {len(PRODUCTS)} products")
    else:
        print(f"  Products already exist ({db.products.count_documents({})} docs), skipping")

    # Orders (with embedded items — classic MongoDB pattern)
    if db.orders.count_documents({}) == 0:
        docs = []
        for o in ORDERS:
            doc = {**o, "_id": o["id"]}
            docs.append(doc)
        db.orders.insert_many(docs)
        print(f"  Inserted {len(ORDERS)} orders (with embedded line items)")
    else:
        print(f"  Orders already exist ({db.orders.count_documents({})} docs), skipping")

    # Reviews
    if db.reviews.count_documents({}) == 0:
        db.reviews.insert_many([{**r, "_id": r["id"]} for r in REVIEWS])
        print(f"  Inserted {len(REVIEWS)} reviews")
    else:
        print(f"  Reviews already exist ({db.reviews.count_documents({})} docs), skipping")

    # DB-specific: activity_log (nested docs, arrays, mixed types)
    if db.activity_log.count_documents({}) == 0:
        actions = ["view_product", "add_to_cart", "purchase", "search", "login", "logout"]
        devices = ["desktop", "mobile", "tablet"]
        logs = []
        base = datetime.now(timezone.utc) - timedelta(days=30)
        for i in range(100):
            cust = random.choice(CUSTOMERS)
            action = random.choice(actions)
            entry = {
                "customer_id": cust["id"],
                "customer_name": cust["name"],
                "action": action,
                "timestamp": (base + timedelta(minutes=random.randint(0, 43200))).isoformat(),
                "device": random.choice(devices),
                "metadata": {},
            }
            if action == "view_product":
                p = random.choice(PRODUCTS)
                entry["metadata"] = {"product_id": p["id"], "product_name": p["name"]}
            elif action == "search":
                entry["metadata"] = {"query": random.choice(["laptop", "chair", "cable", "headphones", "desk"])}
            elif action == "add_to_cart":
                p = random.choice(PRODUCTS)
                entry["metadata"] = {"product_id": p["id"], "quantity": random.randint(1, 3)}
            logs.append(entry)
        db.activity_log.insert_many(logs)
        print(f"  Inserted 100 activity_log entries")

    # Create useful indexes
    db.customers.create_index("email", unique=True)
    db.customers.create_index("state")
    db.products.create_index("category")
    db.orders.create_index("customer_id")
    db.orders.create_index("status")
    db.activity_log.create_index("customer_id")
    db.activity_log.create_index("action")
    print("  Created indexes")

    client.close()
    return True


# ===========================================================================
# Redis
# ===========================================================================

def seed_redis(host="localhost", port=6380, clean=False):
    """Seed Redis with e-commerce hashes, sets, sorted sets + session/cache data."""
    try:
        import redis as redis_lib
    except ImportError:
        print("  SKIP redis not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  Redis  ({host}:{port})")
    print(f"{'='*60}")

    r = redis_lib.Redis(host=host, port=port, db=0, decode_responses=True, socket_connect_timeout=5)
    try:
        r.ping()
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    if clean:
        r.flushdb()
        print("  Flushed database 0")

    pipe = r.pipeline()

    # Customer hashes
    for c in CUSTOMERS:
        key = f"customer:{c['id']}"
        pipe.hset(key, mapping={
            "name": c["name"],
            "email": c["email"],
            "city": c["city"],
            "state": c["state"],
        })
    pipe.execute()
    print(f"  Set {len(CUSTOMERS)} customer:* hashes")

    # Product hashes + sorted set for top products by price
    pipe = r.pipeline()
    for p in PRODUCTS:
        key = f"product:{p['id']}"
        pipe.hset(key, mapping={
            "name": p["name"],
            "category": p["category"],
            "price": str(p["price"]),
            "stock": str(p["stock"]),
        })
        pipe.zadd("top_products", {p["name"]: p["price"]})
    pipe.execute()
    print(f"  Set {len(PRODUCTS)} product:* hashes + top_products sorted set")

    # Category sets (product IDs per category)
    pipe = r.pipeline()
    for p in PRODUCTS:
        pipe.sadd(f"category:{p['category']}", p["id"])
    pipe.execute()
    categories = set(p["category"] for p in PRODUCTS)
    print(f"  Set {len(categories)} category:* sets")

    # Order hashes
    pipe = r.pipeline()
    for o in ORDERS:
        key = f"order:{o['id']}"
        pipe.hset(key, mapping={
            "customer_id": str(o["customer_id"]),
            "status": o["status"],
            "total_amount": str(o["total_amount"]),
            "order_date": o["order_date"],
            "num_items": str(len(o["items"])),
        })
        # Track orders per customer
        pipe.sadd(f"customer:{o['customer_id']}:orders", o["id"])
    pipe.execute()
    print(f"  Set {len(ORDERS)} order:* hashes + customer:*:orders sets")

    # DB-specific: sessions with TTL
    pipe = r.pipeline()
    for i in range(20):
        cust = random.choice(CUSTOMERS)
        session_data = json.dumps({
            "customer_id": cust["id"],
            "customer_name": cust["name"],
            "cart_items": random.randint(0, 5),
            "last_active": datetime.now(timezone.utc).isoformat(),
        })
        pipe.setex(f"session:{i+1}", 3600, session_data)
    pipe.execute()
    print("  Set 20 session:* keys (1h TTL)")

    # DB-specific: cache entries
    pipe = r.pipeline()
    for p in PRODUCTS[:10]:
        pipe.setex(f"cache:product_detail:{p['id']}", 300, json.dumps(p))
    pipe.execute()
    print("  Set 10 cache:product_detail:* keys (5m TTL)")

    # DB-specific: rate limit counters
    pipe = r.pipeline()
    for c in CUSTOMERS[:5]:
        pipe.setex(f"rate_limit:api:{c['id']}", 60, str(random.randint(1, 50)))
    pipe.execute()
    print("  Set 5 rate_limit:api:* counters (60s TTL)")

    r.close()
    return True


# ===========================================================================
# Cassandra
# ===========================================================================

def seed_cassandra(host="localhost", port=9042, clean=False):
    """Seed Cassandra with e-commerce tables + time-series sensor data."""
    try:
        from cassandra.cluster import Cluster
    except ImportError:
        print("  SKIP cassandra-driver not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  Cassandra  ({host}:{port})")
    print(f"{'='*60}")

    try:
        cluster = Cluster([host], port=port, connect_timeout=10)
        session = cluster.connect()
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    keyspace = "ecommerce"

    if clean:
        session.execute(f"DROP KEYSPACE IF EXISTS {keyspace}")
        print(f"  Dropped keyspace '{keyspace}'")

    # Create keyspace
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {keyspace}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)
    session.set_keyspace(keyspace)

    # customers_by_id
    session.execute("""
        CREATE TABLE IF NOT EXISTS customers_by_id (
            customer_id int PRIMARY KEY,
            name text,
            email text,
            city text,
            state text
        )
    """)
    for c in CUSTOMERS:
        session.execute(
            "INSERT INTO customers_by_id (customer_id, name, email, city, state) VALUES (%s, %s, %s, %s, %s)",
            (c["id"], c["name"], c["email"], c["city"], c["state"])
        )
    print(f"  Inserted {len(CUSTOMERS)} rows into customers_by_id")

    # products_by_category (partition key = category)
    session.execute("""
        CREATE TABLE IF NOT EXISTS products_by_category (
            category text,
            product_id int,
            name text,
            price decimal,
            stock int,
            PRIMARY KEY (category, product_id)
        )
    """)
    for p in PRODUCTS:
        session.execute(
            "INSERT INTO products_by_category (category, product_id, name, price, stock) VALUES (%s, %s, %s, %s, %s)",
            (p["category"], p["id"], p["name"], Decimal(str(p["price"])), p["stock"])
        )
    print(f"  Inserted {len(PRODUCTS)} rows into products_by_category")

    # orders_by_customer (partition key = customer_id, clustering = order_date DESC)
    session.execute("""
        CREATE TABLE IF NOT EXISTS orders_by_customer (
            customer_id int,
            order_date timestamp,
            order_id int,
            status text,
            total_amount decimal,
            PRIMARY KEY (customer_id, order_date, order_id)
        ) WITH CLUSTERING ORDER BY (order_date DESC, order_id ASC)
    """)
    for o in ORDERS:
        session.execute(
            "INSERT INTO orders_by_customer (customer_id, order_date, order_id, status, total_amount) VALUES (%s, %s, %s, %s, %s)",
            (o["customer_id"], datetime.fromisoformat(o["order_date"]), o["id"], o["status"], Decimal(str(o["total_amount"])))
        )
    print(f"  Inserted {len(ORDERS)} rows into orders_by_customer")

    # reviews_by_product (partition key = product_id)
    session.execute("""
        CREATE TABLE IF NOT EXISTS reviews_by_product (
            product_id int,
            review_id int,
            customer_id int,
            rating int,
            comment text,
            created_at timestamp,
            PRIMARY KEY (product_id, review_id)
        )
    """)
    for r in REVIEWS:
        session.execute(
            "INSERT INTO reviews_by_product (product_id, review_id, customer_id, rating, comment, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (r["product_id"], r["id"], r["customer_id"], r["rating"], r["comment"], datetime.fromisoformat(r["created_at"]))
        )
    print(f"  Inserted {len(REVIEWS)} rows into reviews_by_product")

    # DB-specific: sensor_readings time-series (wide-column pattern)
    session.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            sensor_id text,
            reading_date date,
            reading_time timestamp,
            temperature double,
            humidity double,
            pressure double,
            PRIMARY KEY ((sensor_id, reading_date), reading_time)
        ) WITH CLUSTERING ORDER BY (reading_time DESC)
    """)
    sensors = ["sensor-001", "sensor-002", "sensor-003"]
    base = datetime.now(timezone.utc) - timedelta(days=7)
    count = 0
    for sensor in sensors:
        for hour in range(168):  # 7 days * 24 hours
            ts = base + timedelta(hours=hour)
            session.execute(
                "INSERT INTO sensor_readings (sensor_id, reading_date, reading_time, temperature, humidity, pressure) VALUES (%s, %s, %s, %s, %s, %s)",
                (sensor, ts.date(), ts,
                 round(20 + random.uniform(-5, 10), 1),
                 round(40 + random.uniform(-10, 20), 1),
                 round(1013 + random.uniform(-10, 10), 1))
            )
            count += 1
    print(f"  Inserted {count} rows into sensor_readings (time-series)")

    cluster.shutdown()
    return True


# ===========================================================================
# DynamoDB Local
# ===========================================================================

def seed_dynamodb(host="localhost", port=8001, clean=False):
    """Seed DynamoDB Local with e-commerce tables + sessions table."""
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("  SKIP boto3 not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  DynamoDB Local  ({host}:{port})")
    print(f"{'='*60}")

    endpoint = f"http://{host}:{port}"
    try:
        dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=endpoint,
            region_name="us-east-1",
            aws_access_key_id="fakeAccessKeyId",
            aws_secret_access_key="fakeSecretAccessKey",
        )
        client = boto3.client(
            "dynamodb",
            endpoint_url=endpoint,
            region_name="us-east-1",
            aws_access_key_id="fakeAccessKeyId",
            aws_secret_access_key="fakeSecretAccessKey",
        )
        client.list_tables(Limit=1)
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    existing = client.list_tables()["TableNames"]

    def create_table_if_not_exists(name, key_schema, attr_defs, **kwargs):
        if clean and name in existing:
            client.delete_table(TableName=name)
            client.get_waiter("table_not_exists").wait(TableName=name)
            print(f"  Deleted table '{name}'")

        if name not in existing or clean:
            params = {
                "TableName": name,
                "KeySchema": key_schema,
                "AttributeDefinitions": attr_defs,
                "BillingMode": "PAY_PER_REQUEST",
                **kwargs,
            }
            client.create_table(**params)
            client.get_waiter("table_exists").wait(TableName=name)
            print(f"  Created table '{name}'")
            return True
        return False

    # Products table (PK = product_id)
    create_table_if_not_exists(
        "Products",
        [{"AttributeName": "product_id", "KeyType": "HASH"}],
        [{"AttributeName": "product_id", "AttributeType": "N"}],
    )
    products_table = dynamodb.Table("Products")
    with products_table.batch_writer() as batch:
        for p in PRODUCTS:
            batch.put_item(Item={
                "product_id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "price": Decimal(str(p["price"])),
                "stock": p["stock"],
            })
    print(f"  Loaded {len(PRODUCTS)} items into Products")

    # Orders table (PK = customer_id, SK = order_id)
    create_table_if_not_exists(
        "Orders",
        [
            {"AttributeName": "customer_id", "KeyType": "HASH"},
            {"AttributeName": "order_id", "KeyType": "RANGE"},
        ],
        [
            {"AttributeName": "customer_id", "AttributeType": "N"},
            {"AttributeName": "order_id", "AttributeType": "N"},
        ],
    )
    orders_table = dynamodb.Table("Orders")
    with orders_table.batch_writer() as batch:
        for o in ORDERS:
            batch.put_item(Item={
                "customer_id": o["customer_id"],
                "order_id": o["id"],
                "status": o["status"],
                "total_amount": Decimal(str(o["total_amount"])),
                "order_date": o["order_date"],
                "shipped_date": o["shipped_date"] or "N/A",
                "num_items": len(o["items"]),
            })
    print(f"  Loaded {len(ORDERS)} items into Orders")

    # Customers table (PK = customer_id)
    create_table_if_not_exists(
        "Customers",
        [{"AttributeName": "customer_id", "KeyType": "HASH"}],
        [{"AttributeName": "customer_id", "AttributeType": "N"}],
    )
    customers_table = dynamodb.Table("Customers")
    with customers_table.batch_writer() as batch:
        for c in CUSTOMERS:
            batch.put_item(Item={
                "customer_id": c["id"],
                "name": c["name"],
                "email": c["email"],
                "city": c["city"],
                "state": c["state"],
            })
    print(f"  Loaded {len(CUSTOMERS)} items into Customers")

    # DB-specific: Sessions table with TTL
    create_table_if_not_exists(
        "Sessions",
        [{"AttributeName": "session_id", "KeyType": "HASH"}],
        [{"AttributeName": "session_id", "AttributeType": "S"}],
    )
    try:
        client.update_time_to_live(
            TableName="Sessions",
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
        )
    except Exception:
        pass  # TTL may already be enabled
    sessions_table = dynamodb.Table("Sessions")
    with sessions_table.batch_writer() as batch:
        for i in range(20):
            cust = random.choice(CUSTOMERS)
            batch.put_item(Item={
                "session_id": f"sess-{i+1:04d}",
                "customer_id": cust["id"],
                "customer_name": cust["name"],
                "cart_items": random.randint(0, 5),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            })
    print("  Loaded 20 items into Sessions (with TTL)")

    return True


# ===========================================================================
# Elasticsearch
# ===========================================================================

def seed_elasticsearch(host="localhost", port=9200, clean=False):
    """Seed Elasticsearch with e-commerce indices + server logs."""
    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        print("  SKIP elasticsearch not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  Elasticsearch  ({host}:{port})")
    print(f"{'='*60}")

    es = Elasticsearch(f"http://{host}:{port}", request_timeout=10)
    try:
        if not es.ping():
            print("  FAILED to connect")
            return False
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    def ensure_index(name, mappings, docs, id_field):
        if clean and es.indices.exists(index=name):
            es.indices.delete(index=name)
            print(f"  Deleted index '{name}'")

        if not es.indices.exists(index=name):
            es.indices.create(index=name, body={"mappings": mappings})
            print(f"  Created index '{name}'")

        # Bulk index
        from elasticsearch.helpers import bulk
        actions = []
        for doc in docs:
            actions.append({
                "_index": name,
                "_id": doc[id_field] if id_field else None,
                "_source": {k: v for k, v in doc.items()},
            })
        if actions:
            success, _ = bulk(es, actions, raise_on_error=False)
            print(f"  Indexed {success} docs into '{name}'")

    # Products index
    ensure_index("products", {
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "category": {"type": "keyword"},
            "price": {"type": "float"},
            "stock": {"type": "integer"},
        }
    }, PRODUCTS, "id")

    # Customers index
    ensure_index("customers", {
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "email": {"type": "keyword"},
            "city": {"type": "keyword"},
            "state": {"type": "keyword"},
        }
    }, CUSTOMERS, "id")

    # Orders index
    order_docs = []
    for o in ORDERS:
        doc = {**o}
        doc.pop("items", None)  # Flatten for ES
        doc["num_items"] = len(o["items"])
        order_docs.append(doc)
    ensure_index("orders", {
        "properties": {
            "id": {"type": "integer"},
            "customer_id": {"type": "integer"},
            "status": {"type": "keyword"},
            "total_amount": {"type": "float"},
            "order_date": {"type": "date"},
            "shipped_date": {"type": "date"},
            "num_items": {"type": "integer"},
        }
    }, order_docs, "id")

    # Reviews index
    ensure_index("reviews", {
        "properties": {
            "id": {"type": "integer"},
            "product_id": {"type": "integer"},
            "customer_id": {"type": "integer"},
            "rating": {"type": "integer"},
            "comment": {"type": "text"},
            "created_at": {"type": "date"},
        }
    }, REVIEWS, "id")

    # DB-specific: server_logs (timestamped log entries)
    log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]
    services = ["api-gateway", "auth-service", "payment-service", "order-service", "inventory-service"]
    messages = [
        "Request processed successfully",
        "Authentication token expired",
        "Payment gateway timeout",
        "Database connection pool exhausted",
        "Cache miss for key",
        "Rate limit exceeded",
        "Health check passed",
        "Retry attempt {n} for request",
        "Invalid input received",
        "Service started on port {port}",
    ]
    base = datetime.now(timezone.utc) - timedelta(days=7)
    logs = []
    for i in range(500):
        level = random.choices(log_levels, weights=[60, 20, 10, 10])[0]
        ts = base + timedelta(seconds=random.randint(0, 604800))
        logs.append({
            "log_id": i + 1,
            "timestamp": ts.isoformat(),
            "level": level,
            "service": random.choice(services),
            "message": random.choice(messages).format(n=random.randint(1, 3), port=random.choice([8000, 8080, 3000])),
            "response_time_ms": round(random.uniform(5, 2000), 1) if level != "ERROR" else None,
            "status_code": random.choice([200, 201, 204, 400, 401, 403, 404, 500]) if level != "DEBUG" else None,
        })

    ensure_index("server_logs", {
        "properties": {
            "log_id": {"type": "integer"},
            "timestamp": {"type": "date"},
            "level": {"type": "keyword"},
            "service": {"type": "keyword"},
            "message": {"type": "text"},
            "response_time_ms": {"type": "float"},
            "status_code": {"type": "integer"},
        }
    }, logs, "log_id")

    es.close()
    return True


# ===========================================================================
# Main
# ===========================================================================

DB_SEEDERS = {
    "mongodb": seed_mongodb,
    "redis": seed_redis,
    "cassandra": seed_cassandra,
    "dynamodb": seed_dynamodb,
    "elasticsearch": seed_elasticsearch,
}

DEFAULT_PORTS = {
    "mongodb": 27017,
    "redis": 6380,
    "cassandra": 9042,
    "dynamodb": 8001,
    "elasticsearch": 9200,
}


def print_connection_info():
    """Print how to register each DB in Database Guru."""
    print(f"\n{'='*60}")
    print("  Database Guru Connection Registration")
    print(f"{'='*60}")
    print("""
To register these databases in Database Guru, create connections with:

  MongoDB:
    Type: mongodb | Host: localhost | Port: 27017
    Database: ecommerce

  Redis:
    Type: redis | Host: localhost | Port: 6380
    Database: 0

  Cassandra:
    Type: cassandra | Host: localhost | Port: 9042
    Database: ecommerce

  DynamoDB Local:
    Type: dynamodb | Host (Region): us-east-1
    Username (Access Key): fakeAccessKeyId
    Password (Secret Key): fakeSecretAccessKey
    Note: Set DYNAMODB_ENDPOINT=http://localhost:8001 in .env

  Elasticsearch:
    Type: elasticsearch | Host: localhost | Port: 9200
    (No auth required)
""")
    print("Example questions to ask:")
    print("  MongoDB:        'Show all products in Electronics category'")
    print("  Redis:          'What are the top 5 most expensive products?'")
    print("  Cassandra:      'Show orders for customer 3'")
    print("  DynamoDB:       'List all products with stock less than 50'")
    print("  Elasticsearch:  'Find all ERROR logs from payment-service'")


def main():
    parser = argparse.ArgumentParser(description="Seed NoSQL databases with sample data")
    parser.add_argument("--db", type=str, default=None,
                        help="Comma-separated list of databases to seed (default: all)")
    parser.add_argument("--clean", action="store_true",
                        help="Drop and recreate data before seeding")
    parser.add_argument("--mongo-host", default="localhost")
    parser.add_argument("--mongo-port", type=int, default=27017)
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--redis-port", type=int, default=6380)
    parser.add_argument("--cassandra-host", default="localhost")
    parser.add_argument("--cassandra-port", type=int, default=9042)
    parser.add_argument("--dynamodb-host", default="localhost")
    parser.add_argument("--dynamodb-port", type=int, default=8001)
    parser.add_argument("--es-host", default="localhost")
    parser.add_argument("--es-port", type=int, default=9200)
    args = parser.parse_args()

    targets = list(DB_SEEDERS.keys())
    if args.db:
        targets = [t.strip().lower() for t in args.db.split(",")]
        invalid = [t for t in targets if t not in DB_SEEDERS]
        if invalid:
            print(f"Unknown databases: {', '.join(invalid)}")
            print(f"Valid options: {', '.join(DB_SEEDERS.keys())}")
            sys.exit(1)

    host_port = {
        "mongodb": (args.mongo_host, args.mongo_port),
        "redis": (args.redis_host, args.redis_port),
        "cassandra": (args.cassandra_host, args.cassandra_port),
        "dynamodb": (args.dynamodb_host, args.dynamodb_port),
        "elasticsearch": (args.es_host, args.es_port),
    }

    print("NoSQL Sample Data Seeder")
    print(f"Targets: {', '.join(targets)}")
    if args.clean:
        print("Mode: CLEAN (drop + recreate)")

    results = {}
    for db_name in targets:
        host, port = host_port[db_name]
        ok = DB_SEEDERS[db_name](host=host, port=port, clean=args.clean)
        results[db_name] = ok

    # Summary
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for db_name, ok in results.items():
        status = "OK" if ok else ("SKIP" if ok is False else "FAIL")
        print(f"  {db_name:15s} {status}")

    if any(results.values()):
        print_connection_info()

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\nSome databases could not be seeded: {', '.join(failed)}")
        print("Make sure the services are running (docker compose -f docker-compose.nosql.yml up -d)")


if __name__ == "__main__":
    main()
