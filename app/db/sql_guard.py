"""SQL safety policies for read-only querying."""

from __future__ import annotations

import re


class SQLValidationError(ValueError):
    """Raised when a SQL statement does not comply with service policies."""


_MUTATION_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "merge",
    "replace",
    "upsert",
    "create",
    "alter",
    "drop",
    "truncate",
    "rename",
    "grant",
    "revoke",
    "commit",
    "rollback",
    "savepoint",
    "execute",
    "exec",
    "call",
)

_LIMIT_PATTERNS = (
    re.compile(r"\blimit\s+\d+\b", re.IGNORECASE),
    re.compile(r"\btop\s*\(\s*\d+\s*\)\b", re.IGNORECASE),
    re.compile(r"\btop\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bfetch\s+first\s+\d+\s+rows?\s+only\b", re.IGNORECASE),
)


def _strip_sql_comments(sql: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", without_block)


def _mask_string_literals(sql: str) -> str:
    """Replace quoted strings with placeholders to avoid false keyword hits."""
    return re.sub(r"'(?:''|[^'])*'", "''", sql)


def _has_multiple_statements(sql: str) -> bool:
    """Return True if *sql* contains more than one statement."""
    in_single = False
    in_double = False

    for i, ch in enumerate(sql):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ";" and not in_single and not in_double:
            tail = sql[i + 1 :].strip()
            if tail:
                return True

    return False


def validate_sql_query(sql: str) -> None:
    """Validate SQL against read-only and single-statement policies."""
    cleaned = _strip_sql_comments(sql).strip()
    cleaned_masked = _mask_string_literals(cleaned)
    if not cleaned:
        raise SQLValidationError("La consulta SQL está vacía.")

    if _has_multiple_statements(cleaned_masked):
        raise SQLValidationError("Se permite solo una sentencia SQL por consulta.")

    head = cleaned.lower().lstrip("(")
    if not (head.startswith("select") or head.startswith("with")):
        raise SQLValidationError("Solo se permiten consultas de lectura (SELECT).")

    for keyword in _MUTATION_KEYWORDS:
        if re.search(rf"\b{keyword}\b", cleaned_masked, flags=re.IGNORECASE):
            raise SQLValidationError(
                f"La consulta contiene una palabra no permitida: {keyword.upper()}."
            )


def _has_row_limit(sql: str) -> bool:
    return any(pattern.search(sql) for pattern in _LIMIT_PATTERNS)


def apply_row_limit(sql: str, db_model: str, max_rows: int) -> str:
    """Apply a default row limit if the SQL does not declare one explicitly."""
    if max_rows <= 0 or _has_row_limit(sql):
        return sql

    model = db_model.lower()
    if model == "sqlsrv":
        return re.sub(
            r"^\s*select\s+(distinct\s+)?",
            lambda m: f"SELECT {m.group(1) or ''}TOP {max_rows} ",
            sql,
            count=1,
            flags=re.IGNORECASE,
        )

    return f"{sql.rstrip(';')} LIMIT {max_rows}"
