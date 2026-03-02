#!/usr/bin/env python3
"""
Seed SQL databases with sample e-commerce data for testing Database Guru.

Usage:
    python scripts/seed_sql_data.py                          # Seed all databases
    python scripts/seed_sql_data.py --db postgresql,sqlite    # Seed specific databases
    python scripts/seed_sql_data.py --clean                   # Drop and recreate before seeding
    python scripts/seed_sql_data.py --db mysql --clean --mysql-host myhost

Requires: pip install -r requirements-sql-seed.txt
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared sample data (same dataset as seed_nosql_data.py and create_sample_db.py)
# ---------------------------------------------------------------------------

CUSTOMERS = [
    (1, "John Doe", "john.doe@email.com", "New York", "NY"),
    (2, "Jane Smith", "jane.smith@email.com", "Los Angeles", "CA"),
    (3, "Mike Johnson", "mike.j@email.com", "Chicago", "IL"),
    (4, "Sarah Williams", "sarah.w@email.com", "Houston", "TX"),
    (5, "David Brown", "david.brown@email.com", "Phoenix", "AZ"),
    (6, "Emily Davis", "emily.d@email.com", "Philadelphia", "PA"),
    (7, "Chris Wilson", "chris.wilson@email.com", "San Antonio", "TX"),
    (8, "Lisa Anderson", "lisa.a@email.com", "San Diego", "CA"),
    (9, "Tom Martinez", "tom.m@email.com", "Dallas", "TX"),
    (10, "Amy Taylor", "amy.taylor@email.com", "San Jose", "CA"),
    (11, "Robert Lee", "robert.lee@email.com", "Austin", "TX"),
    (12, "Jessica White", "jessica.w@email.com", "Jacksonville", "FL"),
    (13, "James Harris", "james.h@email.com", "San Francisco", "CA"),
    (14, "Linda Clark", "linda.c@email.com", "Columbus", "OH"),
    (15, "Michael Lewis", "michael.l@email.com", "Fort Worth", "TX"),
]

CATEGORIES = [
    (1, "Electronics", "Electronic devices and gadgets"),
    (2, "Accessories", "Product accessories and add-ons"),
    (3, "Office", "Office supplies and stationery"),
    (4, "Furniture", "Office and home furniture"),
]

CATEGORY_MAP = {"Electronics": 1, "Accessories": 2, "Office": 3, "Furniture": 4}

PRODUCTS = [
    (1, "Laptop Pro 15", 1, 1299.99, 45),
    (2, "Wireless Mouse", 1, 29.99, 150),
    (3, "USB-C Cable", 2, 12.99, 200),
    (4, "Mechanical Keyboard", 1, 149.99, 75),
    (5, "Monitor 27 inch", 1, 399.99, 30),
    (6, "Webcam HD", 1, 79.99, 60),
    (7, "Desk Lamp", 3, 34.99, 100),
    (8, "Office Chair", 4, 249.99, 25),
    (9, "Standing Desk", 4, 499.99, 15),
    (10, "Notebook Set", 3, 15.99, 300),
    (11, "Pen Pack", 3, 8.99, 400),
    (12, "Backpack", 2, 59.99, 80),
    (13, "Water Bottle", 2, 19.99, 150),
    (14, "Coffee Mug", 2, 12.99, 200),
    (15, "Headphones", 1, 199.99, 50),
    (16, "Phone Case", 2, 24.99, 180),
    (17, "Screen Protector", 2, 9.99, 250),
    (18, "Charging Pad", 1, 39.99, 90),
    (19, "Bluetooth Speaker", 1, 89.99, 65),
    (20, "Tablet 10 inch", 1, 449.99, 40),
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
    """Generate orders and order_items."""
    orders = []
    order_items = []
    base_date = datetime.now(timezone.utc) - timedelta(days=90)
    item_id = 1

    for i in range(1, num_orders + 1):
        customer_id = random.randint(1, len(CUSTOMERS))
        status = random.choice(ORDER_STATUSES)
        order_date = base_date + timedelta(days=random.randint(0, 90))
        shipped_date = None
        if status in ("shipped", "delivered"):
            shipped_date = order_date + timedelta(days=random.randint(1, 5))

        total = 0.0
        num_items = random.randint(1, 4)
        for _ in range(num_items):
            product = random.choice(PRODUCTS)
            qty = random.randint(1, 3)
            unit_price = product[3]
            line_total = round(unit_price * qty, 2)
            total += line_total
            order_items.append((item_id, i, product[0], qty, unit_price))
            item_id += 1

        orders.append((i, customer_id, round(total, 2), status, order_date, shipped_date))
    return orders, order_items


def generate_reviews(num_reviews=30):
    """Generate reviews."""
    reviews = []
    seen = set()
    rid = 1
    for _ in range(num_reviews + 10):  # extras to account for dedup
        product_id = random.randint(1, len(PRODUCTS))
        customer_id = random.randint(1, len(CUSTOMERS))
        key = (product_id, customer_id)
        if key in seen:
            continue
        seen.add(key)
        reviews.append((
            rid, product_id, customer_id,
            random.randint(1, 5),
            random.choice(REVIEW_COMMENTS),
            datetime.now(timezone.utc) - timedelta(days=random.randint(0, 60)),
        ))
        rid += 1
        if len(reviews) >= num_reviews:
            break
    return reviews


ORDERS, ORDER_ITEMS = generate_orders()
REVIEWS = generate_reviews()


# ---------------------------------------------------------------------------
# Core table DDL per dialect
# ---------------------------------------------------------------------------

PG_CORE_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(100),
    state VARCHAR(2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MYSQL_CORE_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(100),
    state VARCHAR(2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category_id INT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_date TIMESTAMP NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    customer_id INT NOT NULL,
    rating INT CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

SQLITE_CORE_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    city TEXT,
    state TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER,
    price REAL NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    shipped_date DATETIME,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
"""

DUCKDB_CORE_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    city VARCHAR,
    state VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description VARCHAR
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    price DOUBLE NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    total_amount DOUBLE NOT NULL,
    status VARCHAR NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    comment VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _insert_core_data(cursor, execute_fn, paramstyle="qmark"):
    """Insert shared e-commerce data. paramstyle: 'qmark' (?), 'format' (%s), or 'dollar' ($1)."""
    if paramstyle == "qmark":
        ph = "?"
    elif paramstyle == "format":
        ph = "%s"
    else:
        raise ValueError(f"Unknown paramstyle: {paramstyle}")

    p = ph  # shorthand

    # Categories
    for c in CATEGORIES:
        execute_fn(f"INSERT INTO categories (category_id, name, description) VALUES ({p}, {p}, {p})", c)

    # Customers
    for c in CUSTOMERS:
        execute_fn(f"INSERT INTO customers (customer_id, name, email, city, state) VALUES ({p}, {p}, {p}, {p}, {p})", c)

    # Products
    for pr in PRODUCTS:
        execute_fn(f"INSERT INTO products (product_id, name, category_id, price, stock_quantity) VALUES ({p}, {p}, {p}, {p}, {p})", pr)

    # Orders
    for o in ORDERS:
        execute_fn(
            f"INSERT INTO orders (order_id, customer_id, total_amount, status, order_date, shipped_date) VALUES ({p}, {p}, {p}, {p}, {p}, {p})",
            o,
        )

    # Order items
    for oi in ORDER_ITEMS:
        execute_fn(
            f"INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price) VALUES ({p}, {p}, {p}, {p}, {p})",
            oi,
        )

    # Reviews
    for r in REVIEWS:
        execute_fn(
            f"INSERT INTO reviews (review_id, product_id, customer_id, rating, comment, created_at) VALUES ({p}, {p}, {p}, {p}, {p}, {p})",
            r,
        )


# ===========================================================================
# PostgreSQL
# ===========================================================================

def seed_postgresql(host="localhost", port=5433, clean=False):
    """Seed PostgreSQL with e-commerce data + employee hierarchy + audit log."""
    try:
        import psycopg2
    except ImportError:
        print("  SKIP psycopg2 not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  PostgreSQL  ({host}:{port})")
    print(f"{'='*60}")

    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname="ecommerce",
            user="dbguru", password="dbguru", connect_timeout=5,
        )
        conn.autocommit = True
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    cur = conn.cursor()

    if clean:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        print("  Dropped and recreated public schema")

    # Check if data exists
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'customers')")
    tables_exist = cur.fetchone()[0]

    if tables_exist:
        cur.execute("SELECT COUNT(*) FROM customers")
        if cur.fetchone()[0] > 0:
            print("  Data already exists, skipping (use --clean to recreate)")
            conn.close()
            return True

    # Core tables
    for stmt in PG_CORE_DDL.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    print("  Created core tables")

    _insert_core_data(cur, cur.execute, "format")
    print(f"  Inserted {len(CUSTOMERS)} customers, {len(CATEGORIES)} categories, {len(PRODUCTS)} products")
    print(f"  Inserted {len(ORDERS)} orders, {len(ORDER_ITEMS)} order items, {len(REVIEWS)} reviews")

    # PG-specific: employee_hierarchy (recursive CTE demo)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employee_hierarchy (
            employee_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            title VARCHAR(100),
            manager_id INTEGER REFERENCES employee_hierarchy(employee_id),
            department VARCHAR(100),
            salary DECIMAL(10, 2)
        )
    """)
    employees = [
        (1, "Alice Chen", "CEO", None, "Executive", 250000),
        (2, "Bob Martinez", "VP Engineering", 1, "Engineering", 200000),
        (3, "Carol Williams", "VP Sales", 1, "Sales", 190000),
        (4, "Dan Kumar", "Engineering Manager", 2, "Engineering", 160000),
        (5, "Eve Johnson", "Sales Manager", 3, "Sales", 140000),
        (6, "Frank Lee", "Senior Developer", 4, "Engineering", 130000),
        (7, "Grace Park", "Developer", 4, "Engineering", 110000),
        (8, "Henry Wilson", "Junior Developer", 6, "Engineering", 85000),
        (9, "Iris Brown", "Sales Rep", 5, "Sales", 75000),
        (10, "Jack Davis", "Sales Rep", 5, "Sales", 72000),
        (11, "Karen White", "DevOps Engineer", 4, "Engineering", 120000),
        (12, "Leo Garcia", "QA Engineer", 4, "Engineering", 100000),
    ]
    for emp in employees:
        cur.execute(
            "INSERT INTO employee_hierarchy (employee_id, name, title, manager_id, department, salary) VALUES (%s, %s, %s, %s, %s, %s)",
            emp,
        )
    print("  Inserted 12 rows into employee_hierarchy (recursive CTE demo)")

    # PG-specific: audit_log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id SERIAL PRIMARY KEY,
            table_name VARCHAR(100) NOT NULL,
            operation VARCHAR(10) NOT NULL,
            record_id INTEGER,
            old_values JSONB,
            new_values JSONB,
            changed_by VARCHAR(100) DEFAULT 'system',
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    operations = ["INSERT", "UPDATE", "DELETE"]
    tables = ["customers", "products", "orders"]
    base = datetime.now(timezone.utc) - timedelta(days=30)
    for i in range(50):
        op = random.choice(operations)
        tbl = random.choice(tables)
        rec_id = random.randint(1, 20)
        old_val = '{"status": "pending"}' if op != "INSERT" else None
        new_val = '{"status": "shipped"}' if op != "DELETE" else None
        ts = base + timedelta(hours=random.randint(0, 720))
        cur.execute(
            "INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values, changed_at) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s)",
            (tbl, op, rec_id, old_val, new_val, ts),
        )
    print("  Inserted 50 rows into audit_log (JSONB demo)")

    # Reset sequences to max ID + 1
    for table, col in [("customers", "customer_id"), ("categories", "category_id"), ("products", "product_id"),
                       ("orders", "order_id"), ("order_items", "order_item_id"), ("reviews", "review_id"),
                       ("employee_hierarchy", "employee_id"), ("audit_log", "log_id")]:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), COALESCE((SELECT MAX({col}) FROM {table}), 1))")

    conn.close()
    return True


# ===========================================================================
# MySQL
# ===========================================================================

def seed_mysql(host="localhost", port=3307, clean=False):
    """Seed MySQL with e-commerce data + inventory log + customer preferences (JSON)."""
    try:
        import pymysql
    except ImportError:
        print("  SKIP pymysql not installed")
        return False

    print(f"\n{'='*60}")
    print(f"  MySQL  ({host}:{port})")
    print(f"{'='*60}")

    try:
        conn = pymysql.connect(
            host=host, port=port, db="ecommerce",
            user="dbguru", password="dbguru", connect_timeout=5,
        )
    except Exception as e:
        print(f"  FAILED to connect: {e}")
        return False

    cur = conn.cursor()

    if clean:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='ecommerce'")
        for (tbl,) in cur.fetchall():
            cur.execute(f"DROP TABLE IF EXISTS `{tbl}`")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        print("  Dropped all tables")

    # Check if data exists
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='ecommerce' AND table_name='customers'")
    if cur.fetchone()[0] > 0:
        cur.execute("SELECT COUNT(*) FROM customers")
        if cur.fetchone()[0] > 0:
            print("  Data already exists, skipping (use --clean to recreate)")
            conn.close()
            return True

    # Core tables
    for stmt in MYSQL_CORE_DDL.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    print("  Created core tables")

    _insert_core_data(cur, cur.execute, "format")
    conn.commit()
    print(f"  Inserted {len(CUSTOMERS)} customers, {len(CATEGORIES)} categories, {len(PRODUCTS)} products")
    print(f"  Inserted {len(ORDERS)} orders, {len(ORDER_ITEMS)} order items, {len(REVIEWS)} reviews")

    # MySQL-specific: product_inventory_log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_inventory_log (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            change_type VARCHAR(20) NOT NULL,
            quantity_change INT NOT NULL,
            quantity_after INT NOT NULL,
            reason VARCHAR(255),
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    change_types = ["restock", "sale", "return", "adjustment", "damage"]
    reasons = ["Regular restock", "Customer purchase", "Customer return", "Inventory audit", "Damaged in warehouse"]
    base = datetime.now(timezone.utc) - timedelta(days=60)
    for i in range(80):
        pid = random.randint(1, len(PRODUCTS))
        ct = random.choice(change_types)
        qty = random.randint(-5, 20) if ct != "sale" else -random.randint(1, 5)
        after = max(0, PRODUCTS[pid - 1][4] + qty)
        ts = base + timedelta(hours=random.randint(0, 1440))
        cur.execute(
            "INSERT INTO product_inventory_log (product_id, change_type, quantity_change, quantity_after, reason, logged_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (pid, ct, qty, after, random.choice(reasons), ts),
        )
    conn.commit()
    print("  Inserted 80 rows into product_inventory_log")

    # MySQL-specific: customer_preferences (JSON column)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_preferences (
            preference_id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT NOT NULL UNIQUE,
            preferences JSON NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    import json
    themes = ["light", "dark", "auto"]
    currencies = ["USD", "EUR", "GBP", "CAD"]
    for c in CUSTOMERS:
        prefs = json.dumps({
            "theme": random.choice(themes),
            "currency": random.choice(currencies),
            "notifications": {
                "email": random.choice([True, False]),
                "sms": random.choice([True, False]),
                "push": random.choice([True, False]),
            },
            "favorite_categories": random.sample(["Electronics", "Accessories", "Office", "Furniture"], random.randint(1, 3)),
        })
        cur.execute(
            "INSERT INTO customer_preferences (customer_id, preferences) VALUES (%s, %s)",
            (c[0], prefs),
        )
    conn.commit()
    print(f"  Inserted {len(CUSTOMERS)} rows into customer_preferences (JSON column)")

    conn.close()
    return True


# ===========================================================================
# SQLite
# ===========================================================================

def seed_sqlite(db_path=None, clean=False):
    """Seed SQLite with e-commerce data + FTS5 search index."""
    import sqlite3

    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "sample_ecommerce.db")

    print(f"\n{'='*60}")
    print(f"  SQLite  ({db_path})")
    print(f"{'='*60}")

    if clean and Path(db_path).exists():
        Path(db_path).unlink()
        print("  Deleted existing database file")

    # Check if data exists
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM customers")
            if cur.fetchone()[0] > 0:
                print("  Data already exists, skipping (use --clean to recreate)")
                conn.close()
                return True
        except sqlite3.OperationalError:
            pass
        conn.close()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Core tables
    for stmt in SQLITE_CORE_DDL.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    print("  Created core tables")

    _insert_core_data(cur, cur.execute, "qmark")
    conn.commit()
    print(f"  Inserted {len(CUSTOMERS)} customers, {len(CATEGORIES)} categories, {len(PRODUCTS)} products")
    print(f"  Inserted {len(ORDERS)} orders, {len(ORDER_ITEMS)} order items, {len(REVIEWS)} reviews")

    # SQLite-specific: FTS5 search index
    cur.execute("DROP TABLE IF EXISTS product_search")
    cur.execute("""
        CREATE VIRTUAL TABLE product_search USING fts5(
            name, category, description,
            content='products',
            content_rowid='product_id'
        )
    """)
    # Populate FTS index
    cat_names = {c[0]: c[1] for c in CATEGORIES}
    for p in PRODUCTS:
        cat_name = cat_names.get(p[2], "")
        cur.execute(
            "INSERT INTO product_search (rowid, name, category, description) VALUES (?, ?, ?, ?)",
            (p[0], p[1], cat_name, f"{p[1]} - {cat_name} product, ${p[3]:.2f}"),
        )
    conn.commit()
    print(f"  Created FTS5 product_search index ({len(PRODUCTS)} entries)")

    # Create useful indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)")
    conn.commit()
    print("  Created indexes")

    conn.close()
    return True


# ===========================================================================
# DuckDB
# ===========================================================================

def seed_duckdb(db_path=None, clean=False):
    """Seed DuckDB with e-commerce data + sales analytics view."""
    try:
        import duckdb
    except ImportError:
        print("  SKIP duckdb not installed")
        return False

    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "sample_ecommerce.duckdb")

    print(f"\n{'='*60}")
    print(f"  DuckDB  ({db_path})")
    print(f"{'='*60}")

    if clean and Path(db_path).exists():
        Path(db_path).unlink()
        print("  Deleted existing database file")

    # Check if data exists
    if Path(db_path).exists():
        try:
            conn = duckdb.connect(db_path)
            result = conn.execute("SELECT COUNT(*) FROM customers").fetchone()
            if result and result[0] > 0:
                print("  Data already exists, skipping (use --clean to recreate)")
                conn.close()
                return True
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    conn = duckdb.connect(db_path)

    # Core tables
    for stmt in DUCKDB_CORE_DDL.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    print("  Created core tables")

    # DuckDB uses positional params with $1, $2 etc but executemany is easier
    for c in CATEGORIES:
        conn.execute("INSERT INTO categories VALUES (?, ?, ?)", c)
    for c in CUSTOMERS:
        conn.execute("INSERT INTO customers (customer_id, name, email, city, state) VALUES (?, ?, ?, ?, ?)", c)
    for p in PRODUCTS:
        conn.execute("INSERT INTO products (product_id, name, category_id, price, stock_quantity) VALUES (?, ?, ?, ?, ?)", p)
    for o in ORDERS:
        conn.execute("INSERT INTO orders (order_id, customer_id, total_amount, status, order_date, shipped_date) VALUES (?, ?, ?, ?, ?, ?)", o)
    for oi in ORDER_ITEMS:
        conn.execute("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", oi)
    for r in REVIEWS:
        conn.execute("INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?)", r)

    print(f"  Inserted {len(CUSTOMERS)} customers, {len(CATEGORIES)} categories, {len(PRODUCTS)} products")
    print(f"  Inserted {len(ORDERS)} orders, {len(ORDER_ITEMS)} order items, {len(REVIEWS)} reviews")

    # DuckDB-specific: sales_analytics table (OLAP-friendly denormalized view)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales_analytics AS
        SELECT
            o.order_id,
            o.order_date,
            o.status AS order_status,
            c.customer_id,
            c.name AS customer_name,
            c.city AS customer_city,
            c.state AS customer_state,
            p.product_id,
            p.name AS product_name,
            cat.name AS category_name,
            oi.quantity,
            oi.unit_price,
            oi.quantity * oi.unit_price AS line_total,
            o.total_amount AS order_total,
            EXTRACT(YEAR FROM o.order_date) AS order_year,
            EXTRACT(MONTH FROM o.order_date) AS order_month,
            EXTRACT(DOW FROM o.order_date) AS order_day_of_week
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
    """)
    count = conn.execute("SELECT COUNT(*) FROM sales_analytics").fetchone()[0]
    print(f"  Created sales_analytics table ({count} rows, denormalized OLAP view)")

    # DuckDB-specific: monthly_summary
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_summary AS
        SELECT
            EXTRACT(YEAR FROM order_date) AS year,
            EXTRACT(MONTH FROM order_date) AS month,
            COUNT(DISTINCT order_id) AS total_orders,
            COUNT(DISTINCT customer_id) AS unique_customers,
            SUM(line_total) AS total_revenue,
            AVG(line_total) AS avg_line_total,
            SUM(quantity) AS total_items_sold
        FROM sales_analytics
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)
    print("  Created monthly_summary table (pre-aggregated)")

    conn.close()
    return True


# ===========================================================================
# Main
# ===========================================================================

DB_SEEDERS = {
    "postgresql": seed_postgresql,
    "mysql": seed_mysql,
    "sqlite": seed_sqlite,
    "duckdb": seed_duckdb,
}


def print_connection_info():
    """Print how to register each DB in Database Guru."""
    print(f"\n{'='*60}")
    print("  Database Guru Connection Registration")
    print(f"{'='*60}")
    print("""
To register these databases in Database Guru, create connections with:

  PostgreSQL:
    Type: postgresql | Host: localhost | Port: 5433
    Database: ecommerce | Username: dbguru | Password: dbguru

  MySQL:
    Type: mysql | Host: localhost | Port: 3307
    Database: ecommerce | Username: dbguru | Password: dbguru

  SQLite:
    Type: sqlite | Database Path: sample_ecommerce.db

  DuckDB:
    Type: duckdb | Database Path: sample_ecommerce.duckdb
""")
    print("Example questions to ask:")
    print("  PostgreSQL:  'Show the full management chain for each employee'")
    print("  MySQL:       'Which customers prefer dark theme?'")
    print("  SQLite:      'Search for products matching wireless'")
    print("  DuckDB:      'Show monthly revenue trends'")
    print("  Any DB:      'What are the top 5 best-selling products?'")


def main():
    parser = argparse.ArgumentParser(description="Seed SQL databases with sample data")
    parser.add_argument("--db", type=str, default=None,
                        help="Comma-separated list of databases to seed (default: all)")
    parser.add_argument("--clean", action="store_true",
                        help="Drop and recreate data before seeding")
    parser.add_argument("--pg-host", default="localhost")
    parser.add_argument("--pg-port", type=int, default=5433)
    parser.add_argument("--mysql-host", default="localhost")
    parser.add_argument("--mysql-port", type=int, default=3307)
    parser.add_argument("--sqlite-path", default=None,
                        help="SQLite file path (default: sample_ecommerce.db)")
    parser.add_argument("--duckdb-path", default=None,
                        help="DuckDB file path (default: sample_ecommerce.duckdb)")
    args = parser.parse_args()

    targets = list(DB_SEEDERS.keys())
    if args.db:
        targets = [t.strip().lower() for t in args.db.split(",")]
        invalid = [t for t in targets if t not in DB_SEEDERS]
        if invalid:
            print(f"Unknown databases: {', '.join(invalid)}")
            print(f"Valid options: {', '.join(DB_SEEDERS.keys())}")
            sys.exit(1)

    print("SQL Sample Data Seeder")
    print(f"Targets: {', '.join(targets)}")
    if args.clean:
        print("Mode: CLEAN (drop + recreate)")

    results = {}
    for db_name in targets:
        if db_name == "postgresql":
            ok = seed_postgresql(host=args.pg_host, port=args.pg_port, clean=args.clean)
        elif db_name == "mysql":
            ok = seed_mysql(host=args.mysql_host, port=args.mysql_port, clean=args.clean)
        elif db_name == "sqlite":
            ok = seed_sqlite(db_path=args.sqlite_path, clean=args.clean)
        elif db_name == "duckdb":
            ok = seed_duckdb(db_path=args.duckdb_path, clean=args.clean)
        else:
            ok = False
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
        print("For PostgreSQL/MySQL, make sure Docker services are running:")
        print("  docker compose -f docker-compose.sql.yml up -d")


if __name__ == "__main__":
    main()
