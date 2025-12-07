#!/usr/bin/env python3
"""
Initialize DuckDB test database with sample data

Creates:
- products table (id, name, price, created_at)
- 100 sample product records

Usage:
    python scripts/init_duckdb_test.py
"""

import duckdb
from datetime import datetime
import os


def init_duckdb():
    """Initialize DuckDB test database"""
    print("🔧 Initializing DuckDB test database...")

    db_path = 'tests/fixtures/test_pooling.duckdb'

    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Removed existing database: {db_path}")

    # Connect to database
    try:
        conn = duckdb.connect(db_path)
        print(f"✅ Connected to DuckDB: {db_path}")

        # Create products table
        conn.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                price DOUBLE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created products table")

        # Insert sample data
        products = [
            (i, f"Product {i}", 10.0 + i)
            for i in range(1, 101)
        ]

        conn.executemany(
            "INSERT INTO products (id, name, price) VALUES (?, ?, ?)",
            products
        )
        print(f"✅ Inserted {len(products)} sample products")

        # Verify data
        result = conn.execute("SELECT COUNT(*) FROM products").fetchone()
        count = result[0] if result else 0
        print(f"✅ Verified: {count} rows in products table")

        # Create index for better query performance
        conn.execute("CREATE INDEX idx_products_price ON products(price)")
        print("✅ Created index on price column")

        conn.close()
        print("✅ DuckDB test database initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Error initializing DuckDB: {e}")
        return False


if __name__ == "__main__":
    success = init_duckdb()
    exit(0 if success else 1)
