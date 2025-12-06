#!/usr/bin/env python3
"""
Initialize PostgreSQL test database with sample data

Creates:
- products table (id, name, price, created_at)
- 100 sample product records

Usage:
    python scripts/init_postgres_test.py
"""

import asyncio
import asyncpg
from datetime import datetime


async def init_postgres():
    """Initialize PostgreSQL test database"""
    print("🔧 Initializing PostgreSQL test database...")

    # Connect to database
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5433,
            user='test_user',
            password='test_pass',
            database='test_pooling'
        )
        print("✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        return False

    try:
        # Drop existing table if it exists
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")
        print("🗑️  Dropped existing products table")

        # Create products table
        await conn.execute("""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ Created products table")

        # Insert sample data
        products = [
            (f"Product {i}", 10.0 + i)
            for i in range(1, 101)
        ]

        await conn.executemany(
            "INSERT INTO products (name, price) VALUES ($1, $2)",
            products
        )
        print(f"✅ Inserted {len(products)} sample products")

        # Verify data
        count = await conn.fetchval("SELECT COUNT(*) FROM products")
        print(f"✅ Verified: {count} rows in products table")

        # Create index for better query performance
        await conn.execute("CREATE INDEX idx_products_price ON products(price)")
        print("✅ Created index on price column")

        await conn.close()
        print("✅ PostgreSQL test database initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Error initializing PostgreSQL: {e}")
        await conn.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(init_postgres())
    exit(0 if success else 1)
