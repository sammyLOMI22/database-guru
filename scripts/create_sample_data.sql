-- Create sample data for Database Guru testing

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    city VARCHAR(50),
    state VARCHAR(2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'pending'
);

-- Create order_items table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- Insert sample customers
INSERT INTO customers (name, email, city, state) VALUES
('John Doe', 'john@example.com', 'Los Angeles', 'CA'),
('Jane Smith', 'jane@example.com', 'San Francisco', 'CA'),
('Bob Johnson', 'bob@example.com', 'New York', 'NY'),
('Alice Williams', 'alice@example.com', 'Chicago', 'IL'),
('Charlie Brown', 'charlie@example.com', 'San Diego', 'CA'),
('Diana Prince', 'diana@example.com', 'Austin', 'TX'),
('Eve Davis', 'eve@example.com', 'Seattle', 'WA'),
('Frank Miller', 'frank@example.com', 'Boston', 'MA'),
('Grace Lee', 'grace@example.com', 'Portland', 'OR'),
('Henry Wilson', 'henry@example.com', 'San Jose', 'CA')
ON CONFLICT (email) DO NOTHING;

-- Insert sample products
INSERT INTO products (name, price, category, stock_quantity) VALUES
('Laptop Pro 15"', 1299.99, 'Electronics', 50),
('Wireless Mouse', 29.99, 'Electronics', 200),
('Office Chair', 249.99, 'Furniture', 75),
('Standing Desk', 499.99, 'Furniture', 30),
('USB-C Hub', 49.99, 'Electronics', 150),
('Noise Cancelling Headphones', 199.99, 'Electronics', 100),
('Monitor 27"', 349.99, 'Electronics', 60),
('Keyboard Mechanical', 129.99, 'Electronics', 80),
('Desk Lamp LED', 39.99, 'Furniture', 120),
('Webcam HD', 79.99, 'Electronics', 90);

-- Insert sample orders
INSERT INTO orders (customer_id, total_amount, status) VALUES
(1, 1349.98, 'completed'),
(2, 579.98, 'completed'),
(3, 249.99, 'pending'),
(4, 1299.99, 'completed'),
(5, 349.99, 'shipped'),
(1, 449.98, 'completed'),
(6, 79.99, 'pending'),
(7, 1549.97, 'completed'),
(8, 199.99, 'shipped'),
(2, 129.99, 'completed');

-- Insert sample order items
INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(1, 1, 1, 1299.99),
(1, 2, 1, 29.99),
(1, 5, 1, 49.99),
(2, 3, 1, 249.99),
(2, 7, 1, 349.99),
(3, 3, 1, 249.99),
(4, 1, 1, 1299.99),
(5, 7, 1, 349.99),
(6, 2, 2, 29.99),
(6, 9, 1, 39.99),
(6, 5, 1, 49.99),
(7, 10, 1, 79.99),
(8, 1, 1, 1299.99),
(8, 3, 1, 249.99),
(9, 6, 1, 199.99),
(10, 8, 1, 129.99);
