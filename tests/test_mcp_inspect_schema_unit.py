import pyodbc
import pytest

from mcp_server.tools import inspect_schema as inspect_schema_module


class _FakeCursor:
    def __init__(self, results: list[list[tuple]]):
        self._results = list(results)
        self._current: list[tuple] = []

    def execute(self, sql, *args):
        self._current = self._results.pop(0)

    def fetchall(self):
        return self._current


class _FakeConnection:
    timeout = None

    def __init__(self, results: list[list[tuple]]):
        self._cursor = _FakeCursor(results)

    def cursor(self):
        return self._cursor

    def close(self):
        pass


class _RaisingCursor:
    def __init__(self, exc: Exception):
        self._exc = exc

    def execute(self, sql, *args):
        raise self._exc


class _RaisingConnection:
    timeout = None

    def __init__(self, exc: Exception):
        self._cursor = _RaisingCursor(exc)

    def cursor(self):
        return self._cursor

    def close(self):
        pass


class _TimeoutAssignmentRaisingConnection:
    """connection.timeout 대입 자체가 pyodbc.Error를 던지는 Fake."""

    def __init__(self, exc: Exception):
        self._exc = exc

    @property
    def timeout(self):
        return None

    @timeout.setter
    def timeout(self, value):
        raise self._exc

    def cursor(self):
        raise AssertionError("cursor() must not be reached if the timeout assignment already failed")

    def close(self):
        pass


class _CursorCallRaisingConnection:
    """connection.cursor() 호출 자체가 pyodbc.Error를 던지는 Fake."""

    timeout = None

    def __init__(self, exc: Exception):
        self._exc = exc

    def cursor(self):
        raise self._exc

    def close(self):
        pass


def test_fk_grouping_does_not_merge_same_name_across_different_tables(monkeypatch):
    """object_id 대신 fk_name만으로 Grouping하면 서로 다른 Schema/Table의 동일 이름 FK가
    하나로 합쳐진다. object_id 기반 Grouping이 이를 분리해야 한다."""
    fk_rows = [
        (101, "FK_Same_Name", "SchemaA", "TableA", "ColA1", "SchemaA", "TableRef", "RefCol1", 1),
        (102, "FK_Same_Name", "SchemaB", "TableB", "ColB1", "SchemaB", "TableRef2", "RefCol1", 1),
    ]
    results = [[], [], fk_rows, []]  # columns, primary_key, foreign_key, description
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _FakeConnection(results))

    result = inspect_schema_module._inspect_schema_sync("corr-1")

    assert len(result["foreign_keys"]) == 2
    source_tables = {fk["source_table"] for fk in result["foreign_keys"]}
    assert source_tables == {"TableA", "TableB"}
    for fk in result["foreign_keys"]:
        assert fk["foreign_key_name"] == "FK_Same_Name"
        assert len(fk["source_columns"]) == 1
        assert len(fk["target_columns"]) == 1


def test_fk_composite_columns_preserve_constraint_column_order(monkeypatch):
    fk_rows = [
        (201, "FK_Composite", "Sales", "OrderDetail", "OrderID", "Sales", "Order", "OrderID", 1),
        (201, "FK_Composite", "Sales", "OrderDetail", "LineNo", "Sales", "Order", "LineNo", 2),
    ]
    results = [[], [], fk_rows, []]
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _FakeConnection(results))

    result = inspect_schema_module._inspect_schema_sync("corr-1")

    assert len(result["foreign_keys"]) == 1
    fk = result["foreign_keys"][0]
    assert fk["source_columns"] == ["OrderID", "LineNo"]
    assert fk["target_columns"] == ["OrderID", "LineNo"]


def test_inspect_schema_does_not_leak_raw_pyodbc_error_text(monkeypatch):
    marker = "SECRET-MARKER-schema-inspection"
    exc = pyodbc.Error("42000", f"[Driver] detail {marker} PWD=hunter2;SERVER=internal-host,1433")
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _RaisingConnection(exc))

    with pytest.raises(RuntimeError) as excinfo:
        inspect_schema_module._inspect_schema_sync("corr-1")

    assert marker not in str(excinfo.value)
    assert "hunter2" not in str(excinfo.value)
    assert "internal-host" not in str(excinfo.value)


def test_inspect_schema_still_distinguishes_timeout_from_generic_failure(monkeypatch):
    marker = "SECRET-MARKER-schema-timeout"
    exc = pyodbc.Error("HYT00", f"[Driver] Query timeout expired {marker}")
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _RaisingConnection(exc))

    with pytest.raises(TimeoutError) as excinfo:
        inspect_schema_module._inspect_schema_sync("corr-1")

    assert marker not in str(excinfo.value)


def test_inspect_schema_does_not_leak_raw_pyodbc_error_text_from_timeout_assignment(monkeypatch):
    """connection.timeout 설정 자체가 실패해도(예: 이미 끊긴 Connection) 원본 Driver
    문자열이 새어나가지 않아야 한다."""
    marker = "SECRET-MARKER-schema-connection-setup-failure"
    exc = pyodbc.Error("42000", f"[Driver] detail {marker} PWD=hunter2;SERVER=internal-host,1433")
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _TimeoutAssignmentRaisingConnection(exc))

    with pytest.raises(RuntimeError) as excinfo:
        inspect_schema_module._inspect_schema_sync("corr-1")

    assert marker not in str(excinfo.value)
    assert "hunter2" not in str(excinfo.value)
    assert "internal-host" not in str(excinfo.value)


def test_inspect_schema_does_not_leak_raw_pyodbc_error_text_from_cursor_call(monkeypatch):
    """connection.cursor() 호출 자체가 실패해도 원본 Driver 문자열이 새어나가지 않아야 한다."""
    marker = "SECRET-MARKER-schema-cursor-call"
    exc = pyodbc.Error("42000", f"[Driver] detail {marker} PWD=hunter2;SERVER=internal-host,1433")
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _CursorCallRaisingConnection(exc))

    with pytest.raises(RuntimeError) as excinfo:
        inspect_schema_module._inspect_schema_sync("corr-1")

    assert marker not in str(excinfo.value)
    assert "hunter2" not in str(excinfo.value)
    assert "internal-host" not in str(excinfo.value)


def test_inspect_schema_still_distinguishes_timeout_at_cursor_call(monkeypatch):
    marker = "SECRET-MARKER-schema-cursor-timeout"
    exc = pyodbc.Error("HYT00", f"[Driver] Query timeout expired {marker}")
    monkeypatch.setattr(inspect_schema_module.db, "get_connection", lambda: _CursorCallRaisingConnection(exc))

    with pytest.raises(TimeoutError) as excinfo:
        inspect_schema_module._inspect_schema_sync("corr-1")

    assert marker not in str(excinfo.value)
