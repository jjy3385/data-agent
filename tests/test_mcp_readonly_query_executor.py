import datetime
from decimal import Decimal

import pyodbc
import pytest

from mcp_server import readonly_query_executor as executor


def test_validate_sql_accepts_plain_select():
    assert executor._validate_sql("SELECT 1") == "SELECT 1"


def test_validate_sql_strips_trailing_semicolon():
    assert executor._validate_sql("SELECT 1;") == "SELECT 1"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1;;",
        "SELECT 1;;;",
        "SELECT 1; SELECT 2",
        "SELECT 1;; SELECT 2",
    ],
)
def test_validate_sql_rejects_multiple_trailing_semicolons(sql):
    """rstrip(';')는 후행 세미콜론을 전부 지워 'SELECT 1;;;'을 통과시켰다. 단일 후행
    세미콜론 하나만 제거하고 남은 세미콜론은 다중 Statement로 거부해야 한다."""
    with pytest.raises(ValueError):
        executor._validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE Production.Product SET Name = 'x'",
        "DELETE FROM Production.Product",
        "INSERT INTO Production.Product (Name) VALUES ('x')",
        "DROP TABLE Production.Product",
        "ALTER TABLE Production.Product ADD Foo int",
        "EXEC sp_who",
        "SELECT * INTO NewTable FROM Production.Product",
        "TRUNCATE TABLE Production.Product",
        "GRANT SELECT ON Production.Product TO public",
    ],
)
def test_validate_sql_rejects_forbidden_keywords(sql):
    with pytest.raises(ValueError):
        executor._validate_sql(sql)


def test_validate_sql_rejects_non_select_start():
    with pytest.raises(ValueError):
        executor._validate_sql("WITH cte AS (SELECT 1 AS x) SELECT * FROM cte")


def test_validate_sql_rejects_multiple_statements():
    with pytest.raises(ValueError):
        executor._validate_sql("SELECT 1; SELECT 2")


def test_validate_sql_rejects_line_comment():
    with pytest.raises(ValueError):
        executor._validate_sql("SELECT 1 -- comment")


def test_validate_sql_rejects_block_comment():
    with pytest.raises(ValueError):
        executor._validate_sql("SELECT 1 /* comment */")


def test_validate_sql_rejects_blank():
    with pytest.raises(ValueError):
        executor._validate_sql("   ")


@pytest.mark.parametrize("query_timeout_seconds", [0, 16, -1])
def test_validate_input_rejects_out_of_range_query_timeout(query_timeout_seconds):
    with pytest.raises(ValueError):
        executor._validate_input(query_timeout_seconds, 100)


@pytest.mark.parametrize("maximum_returned_rows", [0, 501, -5])
def test_validate_input_rejects_out_of_range_max_rows(maximum_returned_rows):
    with pytest.raises(ValueError):
        executor._validate_input(1, maximum_returned_rows)


@pytest.mark.parametrize(
    "query_timeout_seconds,maximum_returned_rows",
    [(1, 1), (15, 500), (7, 250)],
)
def test_validate_input_accepts_boundary_values(query_timeout_seconds, maximum_returned_rows):
    executor._validate_input(query_timeout_seconds, maximum_returned_rows)


def test_serialize_value_handles_none():
    assert executor._serialize_value(None) is None


def test_serialize_value_handles_decimal():
    assert executor._serialize_value(Decimal("3.140")) == "3.140"


def test_serialize_value_handles_datetime():
    value = datetime.datetime(2026, 1, 2, 3, 4, 5)
    assert executor._serialize_value(value) == value.isoformat()


def test_serialize_value_handles_date():
    value = datetime.date(2026, 1, 2)
    assert executor._serialize_value(value) == value.isoformat()


def test_serialize_value_handles_bytes():
    assert executor._serialize_value(b"\x01\x02") == "0102"


def test_serialize_value_passes_through_plain_types():
    assert executor._serialize_value(42) == 42
    assert executor._serialize_value("text") == "text"
    assert executor._serialize_value(True) is True


def test_execute_does_not_leak_raw_pyodbc_error_text(monkeypatch):
    """DB 쿼리 실행 실패의 RuntimeError 메시지에 원본 Driver 오류 문자열(Secret-like Marker,
    Connection String 조각 포함 가능)이 그대로 담기지 않아야 한다."""
    marker = "SECRET-MARKER-driver-detail-do-not-leak"
    driver_message = f"[Driver] some detail {marker} PWD=hunter2;SERVER=internal-host,1433"

    class _FakeCursor:
        description = None

        def execute(self, sql, params):
            raise pyodbc.Error("42000", driver_message)

    class _FakeConnection:
        timeout = None

        def cursor(self):
            return _FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(executor.db, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(executor.db, "is_timeout_error", lambda exc: False)

    with pytest.raises(RuntimeError) as excinfo:
        executor.execute(sql="SELECT 1", parameters=[], query_timeout_seconds=5, maximum_returned_rows=10)

    assert marker not in str(excinfo.value)
    assert "hunter2" not in str(excinfo.value)
    assert "internal-host" not in str(excinfo.value)


def test_execute_still_distinguishes_timeout_from_generic_failure(monkeypatch):
    marker = "SECRET-MARKER-timeout-path"

    class _FakeCursor:
        description = None

        def execute(self, sql, params):
            raise pyodbc.Error("HYT00", f"[Driver] Query timeout expired {marker}")

    class _FakeConnection:
        timeout = None

        def cursor(self):
            return _FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(executor.db, "get_connection", lambda: _FakeConnection())

    with pytest.raises(TimeoutError) as excinfo:
        executor.execute(sql="SELECT 1", parameters=[], query_timeout_seconds=5, maximum_returned_rows=10)

    assert marker not in str(excinfo.value)
    assert "5s" in str(excinfo.value) or "5" in str(excinfo.value)


def test_execute_does_not_leak_raw_pyodbc_error_text_from_fetchmany(monkeypatch):
    """cursor.execute()는 성공하지만 cursor.fetchmany()가 실패하는 경로도 execute()의 SQL
    실패와 동일한 pyodbc.Error 처리 경계 안에 있어야 하며 원본 Driver 문자열을 노출하지 않는다."""
    marker = "SECRET-MARKER-fetchmany-detail-do-not-leak"
    driver_message = f"[Driver] some detail {marker} PWD=hunter2;SERVER=internal-host,1433"

    class _FakeCursor:
        description = [("n",)]

        def execute(self, sql, params):
            pass

        def fetchmany(self, size):
            raise pyodbc.Error("42000", driver_message)

    class _FakeConnection:
        timeout = None

        def cursor(self):
            return _FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(executor.db, "get_connection", lambda: _FakeConnection())
    monkeypatch.setattr(executor.db, "is_timeout_error", lambda exc: False)

    with pytest.raises(RuntimeError) as excinfo:
        executor.execute(sql="SELECT 1", parameters=[], query_timeout_seconds=5, maximum_returned_rows=10)

    assert str(excinfo.value) == "DB query execution failed"
    assert marker not in str(excinfo.value)
    assert "hunter2" not in str(excinfo.value)
    assert "internal-host" not in str(excinfo.value)


def test_fetchmany_timeout_is_distinguished_from_generic_failure(monkeypatch):
    marker = "SECRET-MARKER-fetchmany-timeout-path"

    class _FakeCursor:
        description = [("n",)]

        def execute(self, sql, params):
            pass

        def fetchmany(self, size):
            raise pyodbc.Error("HYT00", f"[Driver] Query timeout expired {marker}")

    class _FakeConnection:
        timeout = None

        def cursor(self):
            return _FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(executor.db, "get_connection", lambda: _FakeConnection())

    with pytest.raises(TimeoutError) as excinfo:
        executor.execute(sql="SELECT 1", parameters=[], query_timeout_seconds=5, maximum_returned_rows=10)

    assert marker not in str(excinfo.value)
    assert "5" in str(excinfo.value)
