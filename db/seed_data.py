# db/seed_data.py
import sqlite3
import random
import os
from datetime import date, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

# Set paths relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "retail.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")

CATEGORIES = [
    ("Laptops", "Electronics"), ("Smartphones", "Electronics"),
    ("Headphones", "Electronics"), ("Office Chairs", "Furniture"),
    ("Desks", "Furniture"), ("Notebooks", "Stationery"),
    ("Pens", "Stationery"), ("Running Shoes", "Apparel"),
    ("T-Shirts", "Apparel"), ("Kitchenware", "Home"),
]

REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["Consumer", "Corporate", "Small Business"]
STATUSES_WEIGHTED = ["Completed"] * 80 + ["Returned"] * 10 + ["Cancelled"] * 5 + ["Pending"] * 5

def build_schema(conn):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

def seed_categories(conn):
    conn.executemany(
        "INSERT INTO categories (category_name, department) VALUES (?, ?)",
        CATEGORIES,
    )

def seed_products(conn, n=60):
    cats = conn.execute("SELECT category_id, category_name FROM categories").fetchall()
    rows = []
    for i in range(n):
        cat_id, cat_name = random.choice(cats)
        base_price = round(random.uniform(8, 1200), 2)
        cost = round(base_price * random.uniform(0.45, 0.7), 2)
        rows.append((
            f"{cat_name[:-1] if cat_name.endswith('s') else cat_name} {fake.word().capitalize()} {random.choice(['Pro','Lite','Max','Plus',''])}".strip(),
            cat_id, base_price, cost, fake.company(),
            fake.date_between(start_date="-3y", end_date="-6m").isoformat(),
        ))
    conn.executemany(
        "INSERT INTO products (product_name, category_id, unit_price, unit_cost, supplier, launch_date) VALUES (?,?,?,?,?,?)",
        rows,
    )

def seed_customers(conn, n=500):
    rows = []
    for _ in range(n):
        rows.append((
            fake.first_name(), fake.last_name(), fake.unique.email(),
            fake.date_between(start_date="-4y", end_date="today").isoformat(),
            fake.city(), fake.state_abbr(), "USA",
            random.choice(SEGMENTS),
        ))
    conn.executemany(
        "INSERT INTO customers (first_name,last_name,email,signup_date,city,state,country,customer_segment) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )

def seed_employees(conn, n=15):
    roles = ["Sales Rep", "Account Manager", "Regional Lead"]
    rows = [(fake.first_name(), fake.last_name(), random.choice(roles),
              random.choice(REGIONS), fake.date_between(start_date="-5y", end_date="-6m").isoformat())
             for _ in range(n)]
    conn.executemany(
        "INSERT INTO employees (first_name,last_name,role,region,hire_date) VALUES (?,?,?,?,?)",
        rows,
    )

def seed_orders_and_items(conn, n_orders=4000):
    customer_ids = [r[0] for r in conn.execute("SELECT customer_id FROM customers").fetchall()]
    employee_ids = [r[0] for r in conn.execute("SELECT employee_id FROM employees").fetchall()]
    products = conn.execute("SELECT product_id, unit_price FROM products").fetchall()

    order_rows, item_rows = [], []
    start = date.today() - timedelta(days=730)  # 2 years of history

    for oid in range(1, n_orders + 1):
        # Seasonal weighting: more orders in Nov/Dec (holiday effect)
        day_offset = random.randint(0, 730)
        order_date = start + timedelta(days=day_offset)
        boost = 1.6 if order_date.month in (11, 12) else 1.0
        if random.random() > 0.5 * boost and boost == 1.0:
            continue  # thin out non-holiday months slightly for realism

        region = random.choice(REGIONS)
        order_rows.append((
            oid, random.choice(customer_ids), random.choice(employee_ids),
            order_date.isoformat(),
            (order_date + timedelta(days=random.randint(1, 6))).isoformat(),
            random.choices(STATUSES_WEIGHTED)[0],
            region, random.choice(["Credit Card", "PayPal", "Bank Transfer", "Cash on Delivery"]),
        ))

        # 1-4 line items per order
        for _ in range(random.randint(1, 4)):
            pid, price = random.choice(products)
            item_rows.append((
                oid, pid, random.randint(1, 5), price,
                random.choice([0, 0, 0, 5, 10, 15]),  # most orders undiscounted
            ))

    conn.executemany(
        "INSERT INTO orders (order_id,customer_id,employee_id,order_date,ship_date,order_status,region,payment_method) VALUES (?,?,?,?,?,?,?,?)",
        order_rows,
    )
    conn.executemany(
        "INSERT INTO order_items (order_id,product_id,quantity,unit_price,discount_pct) VALUES (?,?,?,?,?)",
        item_rows,
    )

def main():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    build_schema(conn)
    seed_categories(conn)
    seed_products(conn)
    seed_customers(conn)
    seed_employees(conn)
    seed_orders_and_items(conn)
    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH}")

if __name__ == "__main__":
    main()
