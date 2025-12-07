#!/usr/bin/env python3
"""
Initialize MySQL test database with sample data

Creates:
- products table (id, name, price, created_at)
- 100 sample product records

Usage:
    python scripts/init_mysql_test.py
"""

import asyncio
import aiomysql
from datetime import datetime


async def init_mysql():
    """Initialize MySQL test database"""
    print("🔧 Initializing MySQL test database...")

    # Connect to database
    try:
        conn = await aiomysql.connect(
            host='127.0.0.1',
            port=3307,
            user='test_user',
            password='test_pass',
            db='test_pooling'
        )
        print("✅ Connected to MySQL")
    except Exception as e:
        print(f"❌ Failed to connect to MySQL: {e}")
        return False

    try:
        async with conn.cursor() as cursor:
            # Drop existing table if it exists
            await cursor.execute("DROP TABLE IF EXISTS products")
            print("🗑️  Dropped existing products table")

            # Create products table
            await cursor.execute("""
                CREATE TABLE products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✅ Created products table")

            # Insert sample data
            products = [
                (f"Product {i}", 10.0 + i)
                for i in range(1, 101)
            ]

            await cursor.executemany(
                "INSERT INTO products (name, price) VALUES (%s, %s)",
                products
            )
            await conn.commit()
            print(f"✅ Inserted {len(products)} sample products")

            # Verify data
            await cursor.execute("SELECT COUNT(*) FROM products")
            result = await cursor.fetchone()
            count = result[0] if result else 0
            print(f"✅ Verified: {count} rows in products table")

            # Create index for better query performance
            await cursor.execute("CREATE INDEX idx_products_price ON products(price)")
            await conn.commit()
            print("✅ Created index on price column")

        conn.close()
        print("✅ MySQL test database initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Error initializing MySQL: {e}")
        conn.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(init_mysql())
    exit(0 if success else 1)
