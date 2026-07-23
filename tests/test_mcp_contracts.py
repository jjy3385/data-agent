from types import SimpleNamespace

import pytest

from app.mcp.client_manager import MCPStartupError
from app.mcp.contracts import verify_tool_contracts


def _tool(name: str, properties: dict, required: list):
    return SimpleNamespace(
        name=name,
        inputSchema={"type": "object", "properties": properties, "required": required},
    )


def _valid_tools():
    return [
        _tool("inspect_schema", {"correlation_id": {"type": "string"}}, ["correlation_id"]),
        _tool(
            "execute_readonly_query",
            {
                "sql": {"type": "string"},
                "parameters": {"type": "array"},
                "correlation_id": {"type": "string"},
                "query_timeout_seconds": {"type": "integer"},
                "maximum_returned_rows": {"type": "integer"},
            },
            ["sql", "parameters", "correlation_id", "query_timeout_seconds", "maximum_returned_rows"],
        ),
    ]


def test_verify_tool_contracts_accepts_matching_tools():
    verify_tool_contracts(_valid_tools())


def test_verify_tool_contracts_rejects_missing_tool():
    tools = [_valid_tools()[0]]
    with pytest.raises(MCPStartupError) as excinfo:
        verify_tool_contracts(tools)
    assert excinfo.value.reason == "tool_missing"


def test_verify_tool_contracts_rejects_extra_or_missing_property():
    tools = _valid_tools()
    tools[0] = _tool("inspect_schema", {"unexpected_field": {"type": "string"}}, ["unexpected_field"])
    with pytest.raises(MCPStartupError) as excinfo:
        verify_tool_contracts(tools)
    assert excinfo.value.reason == "tool_contract_mismatch"


def test_verify_tool_contracts_rejects_required_mismatch():
    tools = _valid_tools()
    tools[0] = _tool("inspect_schema", {"correlation_id": {"type": "string"}}, [])
    with pytest.raises(MCPStartupError) as excinfo:
        verify_tool_contracts(tools)
    assert excinfo.value.reason == "tool_contract_mismatch"


def test_verify_tool_contracts_rejects_type_mismatch():
    tools = _valid_tools()
    tools[0] = _tool("inspect_schema", {"correlation_id": {"type": "integer"}}, ["correlation_id"])
    with pytest.raises(MCPStartupError) as excinfo:
        verify_tool_contracts(tools)
    assert excinfo.value.reason == "tool_contract_mismatch"
