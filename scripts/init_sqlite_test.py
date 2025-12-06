#!/usr/bin/env python3
"""
Initialize SQLite test database with sample data

Creates:
- products table (id, name, price, created_at)
- 100 sample product records

Usage:
    python scripts/init_sqlite_test.py
"""

import asyncio
import aiosqlite
from datetime import datetime
import os


async def init_sqlite():
    """Initialize SQLite test database"""
    print("🔧 Initializing SQLite test database...")

    db_path = 'tests/fixtures/test_pooling.db'

    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Removed existing database: {db_path}")

    # Connect to database
    try:
        async with aiosqlite.connect(db_path) as db:
            print(f"✅ Connected to SQLite: {db_path}")

            # Create products table
            await db.execute("""
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Created products table")

            # Insert sample data
            products = [
                (f"Product {i}", 10.0 + i)
                for i in range(1, 101)
            ]

            await db.executemany(
                "INSERT INTO products (name, price) VALUES (?, ?)",
                products
            )
            await db.commit()
            print(f"✅ Inserted {len(products)} sample products")

            # Verify data
            async with db.execute("SELECT COUNT(*) FROM products") as cursor:
                result = await cursor.fetchone()
                count = result[0] if result else 0
                print(f"✅ Verified: {count} rows in products table")

            # Create index for better query performance
            await db.execute("CREATE INDEX idx_products_price ON products(price)")
            await db.commit()
            print("✅ Created index on price column")

        print("✅ SQLite test database initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Error initializing SQLite: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(init_sqlite())
    exit(0 if success else 1)
