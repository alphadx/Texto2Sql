"""Database utilities: connection-URL builder, schema extractor, query executor."""

import datetime
import decimal
import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported dialects
# ---------------------------------------------------------------------------

_DIALECTS: Dict[str, str] = {
    "mysql": "mysql+pymysql",
    "mariadb": "mysql+pymysql",
    "sqlsrv": "mssql+pyodbc",
    "sybase": "sybase+pyodbc",
    "postgres": "postgresql+psycopg2",
    "postgresql": "postgresql+psycopg2",
    "sqlite": "sqlite",
}

VALID_DB_MODELS = frozenset(_DIALECTS)

# Default ports per engine
_DEFAULT_PORTS: Dict[str, int] = {
    "mysql": 3306,
    "mariadb": 3306,
    "sqlsrv": 1433,
    "sybase": 5000,
    "postgres": 5432,
    "postgresql": 5432,
    "sqlite": 0,
}


def default_port(db_model: str) -> int:
    """Return the conventional TCP port for *db_model*."""
    return _DEFAULT_PORTS.get(db_model.lower(), 3306)


# ---------------------------------------------------------------------------
# Connection-URL builder
# ---------------------------------------------------------------------------


def build_connection_url(
    db_model: str,
    db_host: str,
    db_user: str,
    db_password: str,
    db_port: int,
    db_name: str,
) -> str:
    """Return a SQLAlchemy connection URL for the given parameters.

    Raises ``ValueError`` for unsupported *db_model* values.
    """
    model = db_model.lower()
    if model not in _DIALECTS:
        raise ValueError(
            f"Unsupported database engine: {db_model!r}. "
            f"Choose from: {', '.join(sorted(_DIALECTS))}."
        )

    if model == "sqlite":
        return f"sqlite:///{db_name}"

    user = quote_plus(db_user)
    password = quote_plus(db_password)
    dialect = _DIALECTS[model]

    if model == "sqlsrv":
        return (
            f"mssql+pyodbc://{user}:{password}@{db_host}:{db_port}/{db_name}"
            "?driver=ODBC+Driver+17+for+SQL+Server"
        )

    return f"{dialect}://{user}:{password}@{db_host}:{db_port}/{db_name}"


# ---------------------------------------------------------------------------
# Schema extractor
# ---------------------------------------------------------------------------


def get_schema(engine: Engine) -> str:
    """Reflect all tables and return a compact DDL-style schema string."""
    inspector = inspect(engine)
    parts: List[str] = []

    for table_name in inspector.get_table_names():
        col_lines: List[str] = []

        for col in inspector.get_columns(table_name):
            nullable = "" if col.get("nullable", True) else " NOT NULL"
            col_lines.append(f"  {col['name']} {col['type']}{nullable}")

        for fk in inspector.get_foreign_keys(table_name):
            constrained = ", ".join(fk["constrained_columns"])
            referred = ", ".join(fk["referred_columns"])
            col_lines.append(
                f"  FOREIGN KEY ({constrained}) "
                f"REFERENCES {fk['referred_table']}({referred})"
            )

        parts.append(
            f"TABLE {table_name} (\n" + ",\n".join(col_lines) + "\n)"
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------


def _value_to_sql_type(value: Any) -> str:
    """Map a Python value to a SQL type name string."""
    if value is None:
        return "unknown"
    # bool must be checked before int (bool is a subclass of int)
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, decimal.Decimal):
        return "decimal"
    if isinstance(value, str):
        return "varchar"
    if isinstance(value, bytes):
        return "binary"
    # datetime must be checked before date (datetime is a subclass of date)
    if isinstance(value, datetime.datetime):
        return "datetime"
    if isinstance(value, datetime.date):
        return "date"
    if isinstance(value, datetime.time):
        return "time"
    return type(value).__name__.lower()


def _serialize_value(value: Any) -> Any:
    """Convert non-JSON-serializable values to JSON-compatible equivalents."""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


# ---------------------------------------------------------------------------
# Query executor
# ---------------------------------------------------------------------------


def execute_query(engine: Engine, sql: str) -> Dict[str, Any]:
    """Execute *sql* and return ``{"columns": [...], "rows": [...]}``.

    Each column entry has ``name`` and ``type`` keys.  Types are inferred
    from the first non-null value in each column; fall back to ``"unknown"``.
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        column_names: List[str] = list(result.keys())
        all_rows = result.fetchall()

    # Infer column types from the first non-null value per column
    col_types = ["unknown"] * len(column_names)
    for row in all_rows:
        for i, val in enumerate(row):
            if col_types[i] == "unknown" and val is not None:
                col_types[i] = _value_to_sql_type(val)
        if all(t != "unknown" for t in col_types):
            break

    columns = [
        {"name": name, "type": col_types[i]}
        for i, name in enumerate(column_names)
    ]
    rows = [[_serialize_value(val) for val in row] for row in all_rows]

    return {"columns": columns, "rows": rows}
