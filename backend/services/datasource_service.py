"""
DataSource Service — Feature 1: Database Connectors
Handles connection building, testing, table discovery, and data fetching
from external databases (SQLite, PostgreSQL, MySQL).
"""
import pandas as pd
from typing import Tuple, Optional, List
from sqlalchemy import create_engine, text, inspect
from models.datasource import DataSource
from datetime import datetime


def build_connection_url(db_type: str, host: str, port: int,
                          database_name: str, username: str, password: str) -> str:
    """Build a SQLAlchemy connection URL from individual fields."""
    if db_type == "sqlite":
        # For SQLite the database_name is the file path
        return f"sqlite:///{database_name}"
    elif db_type == "postgresql":
        return f"postgresql://{username}:{password}@{host}:{port}/{database_name}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def test_connection(connection_url: str) -> Tuple[bool, str, List[str]]:
    """
    Test a DB connection and return discovered table names.
    Returns: (success, message, table_names)
    """
    try:
        engine = create_engine(connection_url, pool_pre_ping=True,
                                connect_args={"connect_timeout": 5} if "postgresql" in connection_url or "mysql" in connection_url else {})
        with engine.connect() as conn:
            # Simple ping
            conn.execute(text("SELECT 1"))
            # Discover tables
            inspector   = inspect(engine)
            table_names = inspector.get_table_names()
        engine.dispose()
        return True, f"Connected successfully. Found {len(table_names)} table(s).", table_names
    except Exception as e:
        msg = str(e)
        if "password authentication" in msg.lower():
            return False, "Authentication failed — check username and password.", []
        if "could not connect" in msg.lower() or "connection refused" in msg.lower():
            return False, "Could not reach the database — check host and port.", []
        if "no such file" in msg.lower():
            return False, "SQLite file not found — check the file path.", []
        return False, f"Connection error: {msg[:300]}", []


def fetch_table_data(connection_url: str, table_name: str,
                     row_limit: int = 5000) -> Tuple[Optional[pd.DataFrame], str]:
    """Fetch data from a specific table."""
    try:
        # Sanitise table name — only allow alphanumeric + underscore
        safe_name = "".join(c for c in table_name if c.isalnum() or c == "_")
        engine = create_engine(connection_url,
                                connect_args={"check_same_thread": False} if "sqlite" in connection_url else {})
        df = pd.read_sql(text(f"SELECT * FROM {safe_name} LIMIT {row_limit}"), engine.connect())
        engine.dispose()
        return df, f"Fetched {len(df)} rows from '{table_name}'."
    except Exception as e:
        return None, f"Failed to fetch table: {str(e)[:200]}"


def get_table_info(connection_url: str) -> List[dict]:
    """Return list of tables with row counts."""
    try:
        engine    = create_engine(connection_url,
                                   connect_args={"check_same_thread": False} if "sqlite" in connection_url else {})
        inspector = inspect(engine)
        tables    = []
        with engine.connect() as conn:
            for tname in inspector.get_table_names():
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar()
                    cols  = len(inspector.get_columns(tname))
                except Exception:
                    count = None; cols = None
                tables.append({"table_name": tname, "row_count": count, "column_count": cols})
        engine.dispose()
        return tables
    except Exception:
        return []
