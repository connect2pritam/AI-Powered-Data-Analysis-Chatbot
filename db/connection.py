# db/connection.py
import os
from sqlalchemy import create_engine, event
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv()

# --- PostgreSQL compatibility functions for SQLite ---
def sqlite_date_trunc(lookup_type, date_str):
    if not date_str:
        return None
    # Support both YYYY-MM-DD and YYYY-MM-DD HH:MM:SS formats
    date_part = date_str.split()[0] if " " in date_str else date_str
    parts = date_part.split('-')
    if len(parts) < 3:
        return date_str
    
    year, month, day = parts[0], parts[1], parts[2]
    lookup = lookup_type.lower()
    if lookup == 'year':
        return f"{year}-01-01"
    elif lookup == 'month':
        return f"{year}-{month}-01"
    elif lookup == 'day':
        return f"{year}-{month}-{day}"
    return date_str

def sqlite_concat(*args):
    return "".join(str(arg) for arg in args if arg is not None)

def sqlite_now():
    from datetime import datetime
    return datetime.now().isoformat()

def register_sqlite_functions(dbapi_connection, connection_record):
    import sqlite3
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Register date_trunc(text, text)
        dbapi_connection.create_function("date_trunc", 2, sqlite_date_trunc)
        # Register concat(...) with variadic inputs (-1)
        dbapi_connection.create_function("concat", -1, sqlite_concat)
        # Register now()
        dbapi_connection.create_function("now", 0, sqlite_now)

def get_db_uri(db_path="data/retail.db"):
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    if not os.path.isabs(db_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, db_path)
    return f"sqlite:///{db_path}"

def get_engine(db_path="data/retail.db"):
    uri = get_db_uri(db_path)
    if uri.startswith("sqlite:///"):
        abs_path = uri.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
    engine = create_engine(uri)
    
    # Register listeners to support postgres functions on SQLite
    if uri.startswith("sqlite:///"):
        event.listen(engine, "connect", register_sqlite_functions)
        
    return engine

def get_langchain_db(db_path="data/retail.db"):
    uri = get_db_uri(db_path)
    if uri.startswith("sqlite:///"):
        abs_path = uri.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
    db = SQLDatabase.from_uri(
        uri,
        sample_rows_in_table_info=3,
    )
    
    # Also register functions on the LangChain SQLAlchemy engine
    if uri.startswith("sqlite:///"):
        event.listen(db._engine, "connect", register_sqlite_functions)
        
    return db
