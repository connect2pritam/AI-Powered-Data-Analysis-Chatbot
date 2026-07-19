-- db/schema.sql

-- Drop existing tables to ensure a clean start if run multiple times
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    signup_date     DATE NOT NULL,
    city            TEXT,
    state           TEXT,
    country         TEXT DEFAULT 'USA',
    customer_segment TEXT CHECK(customer_segment IN ('Consumer','Corporate','Small Business'))
);

CREATE TABLE categories (
    category_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name   TEXT NOT NULL,
    department      TEXT NOT NULL
);

CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name    TEXT NOT NULL,
    category_id     INTEGER REFERENCES categories(category_id),
    unit_price      DECIMAL(10,2) NOT NULL,
    unit_cost       DECIMAL(10,2) NOT NULL,
    supplier        TEXT,
    launch_date     DATE
);

CREATE TABLE employees (
    employee_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    role            TEXT,
    region          TEXT,
    hire_date       DATE
);

CREATE TABLE orders (
    order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER REFERENCES customers(customer_id),
    employee_id     INTEGER REFERENCES employees(employee_id),
    order_date      DATE NOT NULL,
    ship_date       DATE,
    order_status    TEXT CHECK(order_status IN ('Completed','Cancelled','Returned','Pending')),
    region          TEXT,
    payment_method  TEXT
);

CREATE TABLE order_items (
    order_item_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(product_id),
    quantity        INTEGER NOT NULL,
    unit_price      DECIMAL(10,2) NOT NULL,
    discount_pct    DECIMAL(4,2) DEFAULT 0.0
);

-- Helpful indexes for common query patterns
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
