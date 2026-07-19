# tests/test_postgres_emulation.py
import pandas as pd
from db.connection import get_engine

def test_postgres_concat_sqlite():
    engine = get_engine()
    query = "SELECT concat('John', ' ', 'Doe') as full_name;"
    df = pd.read_sql(query, engine)
    assert df.loc[0, "full_name"] == "John Doe"

def test_postgres_date_trunc_sqlite():
    engine = get_engine()
    
    # Test month truncation
    query_month = "SELECT date_trunc('month', '2026-07-18 12:34:56') as truncated_date;"
    df_month = pd.read_sql(query_month, engine)
    assert df_month.loc[0, "truncated_date"] == "2026-07-01"
    
    # Test year truncation
    query_year = "SELECT date_trunc('year', '2026-07-18') as truncated_date;"
    df_year = pd.read_sql(query_year, engine)
    assert df_year.loc[0, "truncated_date"] == "2026-01-01"

def test_postgres_now_sqlite():
    engine = get_engine()
    query = "SELECT now() as current_time;"
    df = pd.read_sql(query, engine)
    val = df.loc[0, "current_time"]
    assert val is not None
    assert "-" in val # Verifies date string format
