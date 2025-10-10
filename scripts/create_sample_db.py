#!/usr/bin/env python3
"""
Create a sample database with realistic e-commerce data for testing Database Guru
"""
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# Sample data
CUSTOMERS = [
    ("John Doe", "john.doe@email.com", "New York", "NY"),
    ("Jane Smith", "jane.smith@email.com", "Los Angeles", "CA"),
    ("Mike Johnson", "mike.j@email.com", "Chicago", "IL"),
    ("Sarah Williams", "sarah.w@email.com", "Houston", "TX"),
    ("David Brown", "david.brown@email.com", "Phoenix", "AZ"),
    ("Emily Davis", "emily.d@email.com", "Philadelphia", "PA"),
    ("Chris Wilson", "chris.wilson@email.com", "San Antonio", "TX"),
    ("Lisa Anderson", "lisa.a@email.com", "San Diego", "CA"),
    ("Tom Martinez", "tom.m@email.com", "Dallas", "TX"),
    ("Amy Taylor", "amy.taylor@email.com", "San Jose", "CA"),
    ("Robert Lee", "robert.lee@email.com", "Austin", "TX"),
    ("Jessica White", "jessica.w@email.com", "Jacksonville", "FL"),
    ("James Harris", "james.h@email.com", "San Francisco", "CA"),
    ("Linda Clark", "linda.c@email.com", "Columbus", "OH"),
    ("Michael Lewis", "michael.l@email.com", "Fort Worth", "TX"),
]

PRODUCTS = [
    ("Laptop Pro 15", "Electronics", 1299.99, 45),
    ("Wireless Mouse", "Electronics", 29.99, 150),
    ("USB-C Cable", "Accessories", 12.99, 200),
    ("Mechanical Keyboard", "Electronics", 149.99, 75),
    ("Monitor 27 inch", "Electronics", 399.99, 30),
    ("Webcam HD", "Electronics", 79.99, 60),
    ("Desk Lamp", "Office", 34.99, 100),
    ("Office Chair", "Furniture", 249.99, 25),
    ("Standing Desk", "Furniture", 499.99, 15),
    ("Notebook Set", "Office", 15.99, 300),
    ("Pen Pack", "Office", 8.99, 400),
    ("Backpack", "Accessories", 59.99, 80),
    ("Water Bottle", "Accessories", 19.99, 150),
    ("Coffee Mug", "Accessories", 12.99, 200),
    ("Headphones", "Electronics", 199.99, 50),
    ("Phone Case", "Accessories", 24.99, 180),
    ("Screen Protector", "Accessories", 9.99, 250),
    ("Charging Pad", "Electronics", 39.99, 90),
    ("Bluetooth Speaker", "Electronics", 89.99, 65),
    ("Tablet 10 inch", "Electronics", 449.99, 40),
]

CATEGORIES = list(set([p[1] for p in PRODUCTS]))

ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]


def create_database(db_path: str):
    """Create the sample database with schema and data"""

    # Remove existing database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"🗑️  Removed existing database at {db_path}")

    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"📦 Creating sample database at: {db_path}")

    # Create tables
    cursor.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            city TEXT,
            state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            price DECIMAL(10, 2) NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            status TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            shipped_date TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    print("✅ Created tables: customers, categories, products, orders, order_items, reviews")

    # Insert customers
    cursor.executemany(
        "INSERT INTO customers (name, email, city, state) VALUES (?, ?, ?, ?)",
        CUSTOMERS
    )
    print(f"✅ Inserted {len(CUSTOMERS)} customers")

    # Insert categories
    category_data = [
        ("Electronics", "Electronic devices and gadgets"),
        ("Accessories", "Product accessories and add-ons"),
        ("Office", "Office supplies and stationery"),
        ("Furniture", "Office and home furniture"),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        category_data
    )
    print(f"✅ Inserted {len(category_data)} categories")

    # Get category IDs
    category_map = {}
    for row in cursor.execute("SELECT category_id, name FROM categories"):
        category_map[row[1]] = row[0]

    # Insert products with category IDs
    product_data = [
        (name, category_map[category], price, stock)
        for name, category, price, stock in PRODUCTS
    ]
    cursor.executemany(
        "INSERT INTO products (name, category_id, price, stock_quantity) VALUES (?, ?, ?, ?)",
        product_data
    )
    print(f"✅ Inserted {len(PRODUCTS)} products")

    # Generate orders (50 random orders)
    num_orders = 50
    base_date = datetime.now() - timedelta(days=90)

    for i in range(num_orders):
        customer_id = random.randint(1, len(CUSTOMERS))
        status = random.choice(ORDER_STATUSES)
        order_date = base_date + timedelta(days=random.randint(0, 90))

        # Randomly determine shipped date
        shipped_date = None
        if status in ["shipped", "delivered"]:
            shipped_date = order_date + timedelta(days=random.randint(1, 5))

        # Create order
        cursor.execute(
            "INSERT INTO orders (customer_id, status, order_date, shipped_date, total_amount) VALUES (?, ?, ?, ?, ?)",
            (customer_id, status, order_date, shipped_date, 0.0)  # Will update total
        )
        order_id = cursor.lastrowid

        # Add 1-4 random items to the order
        num_items = random.randint(1, 4)
        total_amount = 0.0

        for _ in range(num_items):
            product_id = random.randint(1, len(PRODUCTS))
            quantity = random.randint(1, 3)

            # Get product price
            cursor.execute("SELECT price FROM products WHERE product_id = ?", (product_id,))
            unit_price = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (order_id, product_id, quantity, unit_price)
            )

            total_amount += unit_price * quantity

        # Update order total
        cursor.execute(
            "UPDATE orders SET total_amount = ? WHERE order_id = ?",
            (total_amount, order_id)
        )

    print(f"✅ Inserted {num_orders} orders with line items")

    # Generate reviews (30 random reviews)
    num_reviews = 30
    review_comments = [
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

    for _ in range(num_reviews):
        product_id = random.randint(1, len(PRODUCTS))
        customer_id = random.randint(1, len(CUSTOMERS))
        rating = random.randint(1, 5)
        comment = random.choice(review_comments)

        try:
            cursor.execute(
                "INSERT INTO reviews (product_id, customer_id, rating, comment) VALUES (?, ?, ?, ?)",
                (product_id, customer_id, rating, comment)
            )
        except sqlite3.IntegrityError:
            pass  # Skip duplicate reviews

    print(f"✅ Inserted reviews")

    # Commit and close
    conn.commit()

    # Print statistics
    print("\n📊 Database Statistics:")
    cursor.execute("SELECT COUNT(*) FROM customers")
    print(f"   Customers: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM products")
    print(f"   Products: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM orders")
    print(f"   Orders: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM order_items")
    print(f"   Order Items: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM reviews")
    print(f"   Reviews: {cursor.fetchone()[0]}")

    cursor.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'cancelled'")
    total_revenue = cursor.fetchone()[0] or 0
    print(f"   Total Revenue: ${total_revenue:,.2f}")

    conn.close()

    print(f"\n✨ Sample database created successfully!")
    print(f"📍 Location: {Path(db_path).absolute()}")
    print(f"\n💡 Example questions you can ask Database Guru:")
    print("   • What are the top 5 best-selling products?")
    print("   • Show me all orders from customers in California")
    print("   • What's the average order value?")
    print("   • Which products have the highest ratings?")
    print("   • How many orders were shipped last month?")
    print("   • What's the total revenue by category?")
    print("   • Show me customers who haven't placed orders yet")
    print("   • What products are low in stock?")


if __name__ == "__main__":
    db_path = "sample_ecommerce.db"
    create_database(db_path)
