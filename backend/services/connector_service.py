"""
Database Connector Service
Allows DataWatch to pull data directly from:
  - PostgreSQL
  - MySQL
  - SQLite
  - REST APIs (JSON)
  - CSV files (existing flow)

This is what makes the pipeline monitoring work on REAL data sources,
not just uploaded CSVs.
"""
import pandas as pd
import requests
from typing import Tuple, Optional
from sqlalchemy import create_engine, text


SUPPORTED_CONNECTORS = ["postgresql", "mysql", "sqlite", "api", "csv"]


def test_connection(connector_type: str, connection_url: str, query: str) -> Tuple[bool, str]:
    """
    Test if a connector config is valid before saving.
    Returns (success: bool, message: str)
    """
    try:
        df, msg = fetch_data(connector_type, connection_url, query)
        if df is None:
            return False, msg
        return True, f"Connected successfully. Preview: {len(df)} rows, {len(df.columns)} columns."
    except Exception as e:
        return False, str(e)


def fetch_data(connector_type: str, connection_url: str, query: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Fetch data from any supported connector.
    Returns (DataFrame or None, status message)
    """
    if connector_type in ("postgresql", "mysql", "sqlite"):
        return _fetch_from_database(connection_url, query)
    elif connector_type == "api":
        return _fetch_from_api(connection_url, query)
    else:
        return None, f"Unsupported connector type: {connector_type}"


def _fetch_from_database(connection_url: str, query: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Connect to any SQLAlchemy-supported database and run a query.

    Supports:
      PostgreSQL: postgresql://user:pass@host:5432/dbname
      MySQL:      mysql+pymysql://user:pass@host:3306/dbname
      SQLite:     sqlite:///./path/to/file.db
    """
    try:
        # Safety check — only allow SELECT queries
        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT"):
            return None, "Only SELECT queries are allowed for security."

        engine = create_engine(connection_url, pool_pre_ping=True)
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        if df.empty:
            return None, "Query returned 0 rows. Check your query or table."

        return df, f"Fetched {len(df)} rows from database."

    except Exception as e:
        error_msg = str(e)
        # Make common errors more readable
        if "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
            return None, "Could not connect to database. Check host, port, and credentials."
        if "password authentication" in error_msg.lower():
            return None, "Authentication failed. Check username and password."
        if "does not exist" in error_msg.lower():
            return None, "Database or table does not exist. Check your query."
        return None, f"Database error: {error_msg[:200]}"


def _fetch_from_api(base_url: str, endpoint: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Fetch JSON data from a REST API endpoint.

    base_url:  https://api.example.com
    endpoint:  /v1/sales/data  (or full URL)

    The API must return either:
      - A JSON array:  [{"col": val}, ...]
      - A JSON object with a data key: {"data": [...], "total": 100}
    """
    try:
        url = endpoint if endpoint.startswith("http") else base_url.rstrip("/") + "/" + endpoint.lstrip("/")

        response = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

        # Handle common API response shapes
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # Try common keys where data lives
            for key in ("data", "results", "items", "records", "rows"):
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break
            else:
                # Wrap single object in list
                records = [data]
        else:
            return None, "API response is not JSON array or object."

        if not records:
            return None, "API returned empty data array."

        df = pd.json_normalize(records)
        return df, f"Fetched {len(df)} records from API."

    except requests.exceptions.ConnectionError:
        return None, "Could not reach the API. Check the URL."
    except requests.exceptions.Timeout:
        return None, "API request timed out (15s limit)."
    except requests.exceptions.HTTPError as e:
        return None, f"API returned error: {e.response.status_code}"
    except Exception as e:
        return None, f"API error: {str(e)[:200]}"


def get_connector_display_name(connector_type: str) -> str:
    names = {
        "postgresql": "PostgreSQL",
        "mysql":      "MySQL",
        "sqlite":     "SQLite",
        "api":        "REST API",
        "csv":        "CSV Upload"
    }
    return names.get(connector_type, connector_type)


def get_connection_url_placeholder(connector_type: str) -> str:
    placeholders = {
        "postgresql": "postgresql://username:password@localhost:5432/database_name",
        "mysql":      "mysql+pymysql://username:password@localhost:3306/database_name",
        "sqlite":     "sqlite:///./path/to/your/database.db",
        "api":        "https://api.yourservice.com",
    }
    return placeholders.get(connector_type, "")


def get_query_placeholder(connector_type: str) -> str:
    placeholders = {
        "postgresql": "SELECT * FROM your_table LIMIT 1000",
        "mysql":      "SELECT * FROM your_table LIMIT 1000",
        "sqlite":     "SELECT * FROM your_table LIMIT 1000",
        "api":        "/v1/endpoint/data",
    }
    return placeholders.get(connector_type, "")
