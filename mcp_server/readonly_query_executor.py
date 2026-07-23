import re
import time
from typing import Any

import pyodbc

from mcp_server import db

MIN_QUERY_TIMEOUT_SECONDS = 1
MAX_QUERY_TIMEOUT_SECONDS = 15
MIN_MAXIMUM_RETURNED_ROWS = 1
MAX_MAXIMUM_RETURNED_ROWS = 500

_FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "EXEC",
    "EXECUTE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "INTO",
)
_FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE
)


def _validate_input(query_timeout_seconds: int, maximum_returned_rows: int) -> None:
    if not (MIN_QUERY_TIMEOUT_SECONDS <= query_timeout_seconds <= MAX_QUERY_TIMEOUT_SECONDS):
        raise ValueError(
            f"query_timeout_seconds must be between {MIN_QUERY_TIMEOUT_SECONDS} and "
            f"{MAX_QUERY_TIMEOUT_SECONDS}"
        )
    if not (MIN_MAXIMUM_RETURNED_ROWS <= maximum_returned_rows <= MAX_MAXIMUM_RETURNED_ROWS):
        raise ValueError(
            f"maximum_returned_rows must be between {MIN_MAXIMUM_RETURNED_ROWS} and "
            f"{MAX_MAXIMUM_RETURNED_ROWS}"
        )


def _validate_sql(sql: str) -> str:
    """최소한의 SQL 안전성 검사. 전체 AST 파서가 아니라 단어 경계 기반 키워드 거부다."""
    cleaned = sql.strip()
    if not cleaned:
        raise ValueError("sql must not be blank")

    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if ";" in cleaned:
        raise ValueError("sql must not contain multiple statements")
    if "--" in cleaned or "/*" in cleaned:
        raise ValueError("sql must not contain comments")
    if not re.match(r"(?is)^\s*SELECT\b", cleaned):
        raise ValueError("sql must start with SELECT")

    match = _FORBIDDEN_PATTERN.search(cleaned)
    if match:
        raise ValueError(f"sql must not contain forbidden keyword: {match.group(1).upper()}")

    return cleaned


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.hex()
    type_name = type(value).__name__
    if type_name == "Decimal":
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def execute(
    sql: str,
    parameters: list,
    query_timeout_seconds: int,
    maximum_returned_rows: int,
) -> dict[str, Any]:
    _validate_input(query_timeout_seconds, maximum_returned_rows)
    validated_sql = _validate_sql(sql)

    connection = db.get_connection()
    try:
        start = time.monotonic()
        try:
            connection.timeout = query_timeout_seconds
            cursor = connection.cursor()
            cursor.execute(validated_sql, list(parameters or []))
            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows_raw = cursor.fetchmany(maximum_returned_rows + 1)
        except pyodbc.Error as exc:
            if db.is_timeout_error(exc):
                raise TimeoutError(f"DB query timeout exceeded ({query_timeout_seconds}s)") from exc
            raise RuntimeError("DB query execution failed") from exc

        execution_ms = int((time.monotonic() - start) * 1000)

        truncated = len(rows_raw) > maximum_returned_rows
        limited_rows = rows_raw[:maximum_returned_rows]
        rows = [[_serialize_value(value) for value in row] for row in limited_rows]

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "execution_ms": execution_ms,
        }
    finally:
        connection.close()
