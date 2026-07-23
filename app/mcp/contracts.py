from typing import Any

from app.mcp.client_manager import MCPStartupError

_EXPECTED_TOOLS: dict[str, dict[str, Any]] = {
    "inspect_schema": {
        "properties": {"correlation_id": "string"},
        "required": {"correlation_id"},
    },
    "execute_readonly_query": {
        "properties": {
            "sql": "string",
            "parameters": "array",
            "correlation_id": "string",
            "query_timeout_seconds": "integer",
            "maximum_returned_rows": "integer",
        },
        "required": {
            "sql",
            "parameters",
            "correlation_id",
            "query_timeout_seconds",
            "maximum_returned_rows",
        },
    },
}


def verify_tool_contracts(tools: list) -> None:
    """MCP Server가 보고한 Tool Discovery 결과가 기대하는 입력 Contract와 일치하는지 확인한다."""
    tools_by_name = {tool.name: tool for tool in tools}

    missing = sorted(set(_EXPECTED_TOOLS) - set(tools_by_name))
    if missing:
        raise MCPStartupError(f"Missing required MCP tools: {missing}", reason="tool_missing")

    for name, expected in _EXPECTED_TOOLS.items():
        schema = tools_by_name[name].inputSchema or {}
        properties = schema.get("properties", {})

        actual_names = set(properties)
        expected_names = set(expected["properties"])
        if actual_names != expected_names:
            raise MCPStartupError(
                f"Tool '{name}' input properties mismatch: expected {sorted(expected_names)}, "
                f"got {sorted(actual_names)}",
                reason="tool_contract_mismatch",
            )

        actual_required = set(schema.get("required", []))
        if actual_required != expected["required"]:
            raise MCPStartupError(
                f"Tool '{name}' required fields mismatch: expected {sorted(expected['required'])}, "
                f"got {sorted(actual_required)}",
                reason="tool_contract_mismatch",
            )

        for prop_name, expected_type in expected["properties"].items():
            actual_type = properties.get(prop_name, {}).get("type")
            if actual_type != expected_type:
                raise MCPStartupError(
                    f"Tool '{name}' field '{prop_name}' type mismatch: expected {expected_type}, "
                    f"got {actual_type}",
                    reason="tool_contract_mismatch",
                )
