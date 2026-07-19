# tests/test_guardrails.py
from agent.guardrails import is_select_only, enforce_row_limit, clean_sql

def test_clean_sql():
    sql_with_comments = """
    -- This is a comment
    SELECT * FROM customers; /* another comment */
    """
    cleaned = clean_sql(sql_with_comments)
    assert cleaned == "SELECT * FROM customers;"

def test_is_select_only_valid():
    assert is_select_only("SELECT * FROM customers;") is True
    assert is_select_only("  select first_name, last_name from customers  ") is True
    assert is_select_only("WITH sales AS (SELECT * FROM orders) SELECT * FROM sales;") is True

def test_is_select_only_invalid():
    assert is_select_only("INSERT INTO customers (first_name) VALUES ('John');") is False
    assert is_select_only("UPDATE customers SET first_name = 'John';") is False
    assert is_select_only("DELETE FROM customers;") is False
    assert is_select_only("DROP TABLE customers;") is False
    assert is_select_only("ALTER TABLE customers ADD COLUMN age INT;") is False
    assert is_select_only("SELECT * FROM customers; DROP TABLE orders;") is False
    # Check if empty SQL returns False
    assert is_select_only("") is False

def test_enforce_row_limit():
    assert enforce_row_limit("SELECT * FROM customers") == "SELECT * FROM customers LIMIT 1000;"
    assert enforce_row_limit("SELECT * FROM customers;") == "SELECT * FROM customers LIMIT 1000;"
    assert enforce_row_limit("SELECT * FROM customers LIMIT 50;") == "SELECT * FROM customers LIMIT 50;"
    assert enforce_row_limit("SELECT * FROM customers LIMIT 1000") == "SELECT * FROM customers LIMIT 1000"
