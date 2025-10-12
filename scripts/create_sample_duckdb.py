#!/usr/bin/env python3
"""
Create a sample DuckDB database for testing Database Guru
"""
import duckdb
import os
from pathlib import Path

def create_sample_duckdb():
    """Create a sample e-commerce DuckDB database"""

    # Database file path
    db_path = Path(__file__).parent.parent / "sample_ecommerce.duckdb"

    # Remove existing database if it exists
    if db_path.exists():
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)

    # Create connection
    print(f"Creating DuckDB database: {db_path}")
    conn = duckdb.connect(str(db_path))

    # Create tables
    print("Creating tables...")

    # Categories table
    conn.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            description TEXT
        )
    """)

    # Products table
    conn.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            category_id INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            stock_quantity INTEGER NOT NULL,
            description TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # Customers table
    conn.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            first_name VARCHAR NOT NULL,
            last_name VARCHAR NOT NULL,
            email VARCHAR UNIQUE NOT NULL,
            phone VARCHAR,
            city VARCHAR,
            state VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Orders table
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # Order items table
    conn.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Reviews table
    conn.execute("""
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    print("Inserting sample data...")

    # Insert categories
    conn.execute("""
        INSERT INTO categories (id, name, description) VALUES
        (1, 'Electronics', 'Electronic devices and accessories'),
        (2, 'Clothing', 'Apparel and fashion items'),
        (3, 'Books', 'Physical and digital books'),
        (4, 'Home & Garden', 'Home improvement and garden supplies')
    """)

    # Insert products
    conn.execute("""
        INSERT INTO products (id, name, category_id, price, stock_quantity, description) VALUES
        (1, 'Wireless Headphones', 1, 79.99, 150, 'High-quality wireless headphones with noise cancellation'),
        (2, 'Laptop Stand', 1, 49.99, 200, 'Ergonomic laptop stand for better posture'),
        (3, 'USB-C Cable', 1, 12.99, 500, 'Durable USB-C charging cable'),
        (4, 'Men''s T-Shirt', 2, 24.99, 300, 'Comfortable cotton t-shirt'),
        (5, 'Women''s Jeans', 2, 59.99, 180, 'Classic fit denim jeans'),
        (6, 'Running Shoes', 2, 89.99, 120, 'Lightweight running shoes for athletes'),
        (7, 'Python Programming', 3, 39.99, 80, 'Learn Python programming from scratch'),
        (8, 'Cookbook', 3, 29.99, 100, 'Delicious recipes for home cooking'),
        (9, 'Science Fiction Novel', 3, 19.99, 150, 'Bestselling sci-fi adventure'),
        (10, 'Garden Tools Set', 4, 45.99, 90, 'Complete set of essential garden tools'),
        (11, 'LED Desk Lamp', 4, 34.99, 200, 'Modern LED lamp with adjustable brightness'),
        (12, 'Smart Thermostat', 1, 129.99, 75, 'Wi-Fi enabled smart thermostat'),
        (13, 'Yoga Mat', 2, 29.99, 250, 'Non-slip yoga mat for fitness'),
        (14, 'Coffee Maker', 4, 79.99, 110, 'Programmable coffee maker with timer'),
        (15, 'Bluetooth Speaker', 1, 59.99, 180, 'Portable Bluetooth speaker with 12-hour battery'),
        (16, 'Backpack', 2, 44.99, 140, 'Durable backpack with laptop compartment'),
        (17, 'History Book', 3, 34.99, 70, 'Comprehensive world history'),
        (18, 'Plant Pot Set', 4, 24.99, 300, 'Decorative ceramic plant pots'),
        (19, 'Mechanical Keyboard', 1, 99.99, 95, 'RGB mechanical gaming keyboard'),
        (20, 'Sunglasses', 2, 39.99, 200, 'UV protection polarized sunglasses')
    """)

    # Insert customers
    conn.execute("""
        INSERT INTO customers (id, first_name, last_name, email, phone, city, state) VALUES
        (1, 'John', 'Smith', 'john.smith@email.com', '555-0101', 'New York', 'NY'),
        (2, 'Emma', 'Johnson', 'emma.j@email.com', '555-0102', 'Los Angeles', 'CA'),
        (3, 'Michael', 'Williams', 'mwilliams@email.com', '555-0103', 'Chicago', 'IL'),
        (4, 'Sarah', 'Brown', 'sbrown@email.com', '555-0104', 'Houston', 'TX'),
        (5, 'David', 'Jones', 'djones@email.com', '555-0105', 'Phoenix', 'AZ'),
        (6, 'Lisa', 'Garcia', 'lgarcia@email.com', '555-0106', 'Philadelphia', 'PA'),
        (7, 'James', 'Miller', 'jmiller@email.com', '555-0107', 'San Antonio', 'TX'),
        (8, 'Maria', 'Davis', 'mdavis@email.com', '555-0108', 'San Diego', 'CA'),
        (9, 'Robert', 'Rodriguez', 'rrodriguez@email.com', '555-0109', 'Dallas', 'TX'),
        (10, 'Jennifer', 'Martinez', 'jmartinez@email.com', '555-0110', 'San Jose', 'CA'),
        (11, 'William', 'Hernandez', 'whernandez@email.com', '555-0111', 'Austin', 'TX'),
        (12, 'Linda', 'Lopez', 'llopez@email.com', '555-0112', 'Jacksonville', 'FL'),
        (13, 'Richard', 'Gonzalez', 'rgonzalez@email.com', '555-0113', 'Fort Worth', 'TX'),
        (14, 'Patricia', 'Wilson', 'pwilson@email.com', '555-0114', 'Columbus', 'OH'),
        (15, 'Charles', 'Anderson', 'canderson@email.com', '555-0115', 'San Francisco', 'CA')
    """)

    # Insert orders (sample data)
    conn.execute("""
        INSERT INTO orders (id, customer_id, order_date, total_amount, status) VALUES
        (1, 1, '2024-01-15 10:30:00', 129.98, 'delivered'),
        (2, 2, '2024-01-16 14:22:00', 89.99, 'delivered'),
        (3, 3, '2024-01-17 09:15:00', 179.97, 'delivered'),
        (4, 4, '2024-01-18 16:45:00', 24.99, 'delivered'),
        (5, 5, '2024-01-19 11:30:00', 169.98, 'delivered'),
        (6, 1, '2024-02-01 13:20:00', 59.99, 'delivered'),
        (7, 6, '2024-02-02 10:00:00', 94.98, 'delivered'),
        (8, 7, '2024-02-03 15:30:00', 129.99, 'shipped'),
        (9, 8, '2024-02-04 09:45:00', 79.99, 'shipped'),
        (10, 9, '2024-02-05 14:15:00', 149.97, 'processing')
    """)

    # Insert order items
    conn.execute("""
        INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
        (1, 1, 1, 1, 79.99),
        (2, 1, 2, 1, 49.99),
        (3, 2, 6, 1, 89.99),
        (4, 3, 5, 2, 59.99),
        (5, 3, 19, 1, 99.99),
        (6, 4, 4, 1, 24.99),
        (7, 5, 12, 1, 129.99),
        (8, 5, 15, 1, 59.99),
        (9, 6, 5, 1, 59.99),
        (10, 7, 13, 2, 29.99),
        (11, 7, 18, 1, 24.99),
        (12, 8, 12, 1, 129.99),
        (13, 9, 14, 1, 79.99),
        (14, 10, 1, 1, 79.99),
        (15, 10, 3, 2, 12.99)
    """)

    # Insert reviews
    conn.execute("""
        INSERT INTO reviews (id, product_id, customer_id, rating, review_text, created_at) VALUES
        (1, 1, 1, 5, 'Excellent sound quality and comfortable fit!', '2024-01-20 10:00:00'),
        (2, 6, 2, 4, 'Great shoes, very comfortable for running', '2024-01-21 14:30:00'),
        (3, 5, 3, 5, 'Perfect fit and great quality denim', '2024-01-22 09:00:00'),
        (4, 4, 4, 4, 'Nice t-shirt, fits well', '2024-01-23 16:00:00'),
        (5, 12, 5, 5, 'Love the smart features, easy to use', '2024-01-24 11:00:00'),
        (6, 1, 6, 5, 'Best headphones I''ve ever owned', '2024-02-01 13:00:00'),
        (7, 13, 7, 4, 'Good yoga mat, non-slip as advertised', '2024-02-05 10:30:00'),
        (8, 14, 9, 5, 'Makes great coffee every morning', '2024-02-06 08:00:00'),
        (9, 19, 3, 5, 'Amazing keyboard, love the mechanical keys', '2024-02-07 15:00:00'),
        (10, 15, 1, 4, 'Good speaker with long battery life', '2024-02-08 12:00:00')
    """)

    # Verify data
    print("\nDatabase created successfully!")
    print("\nTable summary:")

    tables = ['categories', 'products', 'customers', 'orders', 'order_items', 'reviews']
    for table in tables:
        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"  {table}: {result[0]} rows")

    conn.close()
    print(f"\nDatabase file: {db_path}")
    print("\nYou can now connect to this database in Database Guru!")
    print(f"Connection string: {db_path}")

if __name__ == "__main__":
    try:
        create_sample_duckdb()
    except Exception as e:
        print(f"Error creating database: {e}")
        import traceback
        traceback.print_exc()
