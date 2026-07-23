import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.mcp import lifecycle as lifecycle_module
from app.mcp.client_manager import MCPClientManager, MCPStartupError

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _valid_tools():
    return [
        SimpleNamespace(
            name="inspect_schema",
            inputSchema={
                "type": "object",
                "properties": {"correlation_id": {"type": "string"}},
                "required": ["correlation_id"],
            },
        ),
        SimpleNamespace(
            name="execute_readonly_query",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "parameters": {"type": "array"},
                    "correlation_id": {"type": "string"},
                    "query_timeout_seconds": {"type": "integer"},
                    "maximum_returned_rows": {"type": "integer"},
                },
                "required": [
                    "sql",
                    "parameters",
                    "correlation_id",
                    "query_timeout_seconds",
                    "maximum_returned_rows",
                ],
            },
        ),
    ]


class _FakeSession:
    def __init__(self, tools=None, initialize_delay: float = 0.0, initialize_error: Exception | None = None):
        self._tools = tools if tools is not None else _valid_tools()
        self._initialize_delay = initialize_delay
        self._initialize_error = initialize_error
        self.entered = False
        self.exited = False

    def __call__(self, read_stream, write_stream):
        return self

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False

    async def initialize(self):
        if self._initialize_delay:
            await asyncio.sleep(self._initialize_delay)
        if self._initialize_error:
            raise self._initialize_error

    async def list_tools(self):
        return SimpleNamespace(tools=self._tools)


class _FakeStdioClient:
    def __init__(self):
        self.entered = False
        self.exited = False
        self.received_params = None

    def __call__(self, params):
        self.received_params = params
        return self

    async def __aenter__(self):
        self.entered = True
        return ("read-stream", "write-stream")

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False


def _patch_transport(monkeypatch, fake_session: _FakeSession):
    fake_stdio = _FakeStdioClient()
    monkeypatch.setattr(lifecycle_module, "stdio_client", fake_stdio)
    monkeypatch.setattr(lifecycle_module, "ClientSession", fake_session)
    return fake_stdio, fake_session


async def test_mcp_lifespan_yields_client_manager_on_success(monkeypatch):
    fake_session = _FakeSession()
    fake_stdio, _ = _patch_transport(monkeypatch, fake_session)

    async with lifecycle_module.mcp_lifespan() as manager:
        assert isinstance(manager, MCPClientManager)

    assert fake_stdio.entered is True
    assert fake_stdio.exited is True
    assert fake_session.entered is True
    assert fake_session.exited is True


async def test_mcp_lifespan_raises_startup_error_on_timeout(monkeypatch):
    monkeypatch.setattr(lifecycle_module, "MCP_STARTUP_TIMEOUT_SECONDS", 0.05)
    fake_session = _FakeSession(initialize_delay=1.0)
    fake_stdio, _ = _patch_transport(monkeypatch, fake_session)

    with pytest.raises(MCPStartupError) as excinfo:
        async with lifecycle_module.mcp_lifespan():
            pass

    assert excinfo.value.reason == "startup_timeout"
    assert fake_stdio.exited is True


async def test_mcp_lifespan_raises_startup_error_on_contract_mismatch(monkeypatch):
    bad_tools = [_valid_tools()[0]]  # missing execute_readonly_query
    fake_session = _FakeSession(tools=bad_tools)
    fake_stdio, _ = _patch_transport(monkeypatch, fake_session)

    with pytest.raises(MCPStartupError) as excinfo:
        async with lifecycle_module.mcp_lifespan():
            pass

    assert excinfo.value.reason == "tool_missing"
    assert fake_stdio.exited is True


async def test_mcp_lifespan_passes_parent_os_environment_to_child_process(monkeypatch):
    """자식 MCP Server 프로세스가 SDK 기본(제한된) 환경만 받으면 부모의 TARGET_DB_* OS
    환경변수가 상속되지 않는다. StdioServerParameters.env로 부모 환경 전체를 명시적으로
    전달해야 한다."""
    monkeypatch.setenv("TARGET_DB_HOST", "dummy-parent-env-host-for-test")
    fake_session = _FakeSession()
    fake_stdio, _ = _patch_transport(monkeypatch, fake_session)

    async with lifecycle_module.mcp_lifespan():
        pass

    assert fake_stdio.received_params is not None
    assert fake_stdio.received_params.env is not None
    assert fake_stdio.received_params.env.get("TARGET_DB_HOST") == "dummy-parent-env-host-for-test"


async def test_mcp_lifespan_does_not_mutate_os_environ(monkeypatch):
    import os

    monkeypatch.setenv("TARGET_DB_HOST", "dummy-parent-env-host-for-test")
    fake_session = _FakeSession()
    _patch_transport(monkeypatch, fake_session)

    before = dict(os.environ)
    async with lifecycle_module.mcp_lifespan():
        pass

    assert dict(os.environ) == before


async def test_mcp_lifespan_wraps_unexpected_exception_as_startup_failed(monkeypatch):
    fake_session = _FakeSession(initialize_error=RuntimeError("subprocess exited"))
    fake_stdio, _ = _patch_transport(monkeypatch, fake_session)

    with pytest.raises(MCPStartupError) as excinfo:
        async with lifecycle_module.mcp_lifespan():
            pass

    assert excinfo.value.reason == "startup_failed"
    assert fake_stdio.exited is True
