# agent/guardrails.py
import re

# Block modifying statements and system configuration commands
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|ATTACH|PRAGMA|REPLACE|CREATE|GRANT|REVOKE)\b", 
    re.IGNORECASE
)

def clean_sql(sql: str) -> str:
    """Removes single-line and multi-line SQL comments and trims whitespace."""
    if not sql:
        return ""
    # Remove single line comments
    sql_no_comments = re.sub(r"--.*?\n", "\n", sql)
    # Remove multiline comments
    sql_no_comments = re.sub(r"/\*.*?\*/", "", sql_no_comments, flags=re.DOTALL)
    return sql_no_comments.strip()

def is_select_only(sql: str) -> bool:
    """Returns True if the SQL is a SELECT statement or a CTE (WITH ...) and contains no forbidden words."""
    cleaned = clean_sql(sql)
    if not cleaned:
        return False
    
    lower_sql = cleaned.lower()
    # Support CTEs (Common Table Expressions) and standard SELECT statements
    is_read_only_start = lower_sql.startswith("select") or lower_sql.startswith("with")
    
    return bool(is_read_only_start and not FORBIDDEN.search(cleaned))

def enforce_row_limit(sql: str, max_rows: int = 1000) -> str:
    """Appends a LIMIT clause if not already specified in the SQL query."""
    cleaned = sql.strip()
    if not cleaned:
        return sql
        
    # Check if limit is specified (ignoring case)
    if "limit" not in cleaned.lower():
        # Remove trailing semicolon if exists
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()
        cleaned = f"{cleaned} LIMIT {max_rows};"
    return cleaned
