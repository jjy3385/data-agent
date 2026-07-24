import pytest

from app.mcp.client_manager import MCPToolExecutionError, MCPTransportError
from app.services import agent_service
from app.services.llm_client import LLMUnavailableError
from tests.conftest import FakeLLMClient, FakeMCPClientManager

pytestmark = pytest.mark.anyio

_RUNTIME_INTENT = {
    "request_type": "lookup",
    "subject": "product",
    "requested_concepts": ["inventory", "safety_stock"],
    "requested_output": "list",
    "explicit_parameters": {},
    "requires_clarification": False,
    "clarification_reason": None,
}

_QUERY_PLAN = {
    "purpose": "안전재고보다 현재 재고가 부족한 제품을 조회한다",
    "entity_id": "product",
    "dimension_ids": ["product_id", "product_name"],
    "metric_ids": ["current_inventory", "safety_stock_level"],
    "filters": [{"filter_id": "below_safety_stock", "parameters": {}}],
    "time_policy_id": None,
    "grain_id": "product",
    "join_ids": ["product_to_product_inventory"],
    "order_by": [{"field_id": "product_id", "direction": "asc"}],
    "limit": 100,
    "depth": 1,
}

_GOOD_SQL = (
    "SELECT TOP (100) p.ProductID AS ProductID, p.Name AS Name, "
    "SUM(pi.Quantity) AS CurrentInventory, p.SafetyStockLevel AS SafetyStockLevel\n"
    "FROM Production.Product AS p\n"
    "INNER JOIN Production.ProductInventory AS pi ON p.ProductID = pi.ProductID\n"
    "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n"
    "HAVING SUM(pi.Quantity) < p.SafetyStockLevel\n"
    "ORDER BY p.ProductID ASC"
)

_CATALOG = None  # 요청 처리 단계에서 참조하지 않으므로 None으로도 충분하다(Startup 전용).


def _happy_llm() -> FakeLLMClient:
    return FakeLLMClient(json_responses=[_RUNTIME_INTENT, _QUERY_PLAN], text_responses=[_GOOD_SQL])


@pytest.mark.parametrize(
    "question",
    [
        "현재 재고가 안전재고보다 부족한 제품을 보여줘.",
        "안전재고 기준에 미달한 품목을 알려줘.",
        "창고별 수량을 합쳤을 때 최소 재고보다 적은 상품은?",
    ],
)
async def test_representative_and_korean_phrasing_variants_succeed(question):
    llm = _happy_llm()
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question=question,
        correlation_id="corr-1",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.CompletedOutcome)
    assert outcome.correlation_id == "corr-1"
    assert outcome.bounded_result.columns
    assert len(mcp.execute_readonly_query_calls) == 1
    assert mcp.execute_readonly_query_calls[0]["correlation_id"] == "corr-1"
    assert mcp.execute_readonly_query_calls[0]["parameters"] == []


async def test_clarification_required_does_not_call_mcp():
    clarification = {
        "request_type": "lookup",
        "subject": "",
        "requested_concepts": [],
        "requested_output": "list",
        "explicit_parameters": {},
        "requires_clarification": True,
        "clarification_reason": "어떤 제품인지 명확하지 않습니다.",
    }
    llm = FakeLLMClient(json_responses=[clarification])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="그거 보여줘",
        correlation_id="corr-2",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.ClarificationRequiredOutcome)
    assert outcome.code == "clarification_required"
    assert mcp.execute_readonly_query_calls == []


async def test_llm_unavailable_during_intent_maps_to_failed():
    llm = FakeLLMClient(fail_with=LLMUnavailableError("no key"))
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-3",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.FailedOutcome)
    assert outcome.code == "llm_unavailable"
    assert mcp.execute_readonly_query_calls == []


_SECRET_MARKER = "SECRET-MARKER-do-not-leak"


async def test_rate_limited_llm_keeps_public_code_but_returns_retry_message():
    """공개 code는 계속 llm_unavailable로 유지하면서 rate_limited일 때만 재시도 안내 메시지를
    반환해야 한다(Codex 재검토 발견)."""
    llm = FakeLLMClient(
        fail_with=LLMUnavailableError(f"quota exceeded {_SECRET_MARKER}", reason="rate_limited")
    )
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-rate-limited",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.FailedOutcome)
    assert outcome.code == "llm_unavailable"
    assert outcome.message == agent_service._RATE_LIMITED_MESSAGE
    assert _SECRET_MARKER not in outcome.message


async def test_generic_provider_error_keeps_default_llm_unavailable_message():
    llm = FakeLLMClient(
        fail_with=LLMUnavailableError(f"boom {_SECRET_MARKER}", reason="provider_error")
    )
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-provider-error",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.FailedOutcome)
    assert outcome.code == "llm_unavailable"
    assert outcome.message == agent_service._LLM_UNAVAILABLE_MESSAGE
    assert _SECRET_MARKER not in outcome.message


async def test_intent_contract_violation_maps_to_rejected():
    llm = FakeLLMClient(json_responses=[{**_RUNTIME_INTENT, "request_type": "not_valid"}])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-4",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.RejectedOutcome)
    assert outcome.code == "intent_contract_violation"
    assert mcp.execute_readonly_query_calls == []


async def test_metadata_not_found_maps_to_rejected():
    out_of_scope_intent = {**_RUNTIME_INTENT, "subject": "supplier", "requested_concepts": ["lead_time"]}
    llm = FakeLLMClient(json_responses=[out_of_scope_intent])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="공급업체 리드타임 알려줘",
        correlation_id="corr-5",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.RejectedOutcome)
    assert outcome.code == "metadata_not_found"
    assert mcp.execute_readonly_query_calls == []


async def test_query_plan_structural_violation_maps_to_rejected():
    llm = FakeLLMClient(json_responses=[_RUNTIME_INTENT, {**_QUERY_PLAN, "metric_ids": []}])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-6",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.RejectedOutcome)
    assert outcome.code == "query_plan_invalid"
    assert mcp.execute_readonly_query_calls == []


async def test_query_plan_missing_required_filter_rejected_before_sql_and_mcp():
    """Codex 발견 1: filters=[]로 안전재고 Filter가 빠진 QueryPlan은 plan_validator가
    거부해야 하며, 이 경우 SQL 생성(LLMClient.complete_text)과 MCP 호출이 전혀 일어나지
    않아야 한다."""
    bad_plan = {**_QUERY_PLAN, "filters": []}
    llm = FakeLLMClient(json_responses=[_RUNTIME_INTENT, bad_plan], text_responses=[_GOOD_SQL])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-6b",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.RejectedOutcome)
    assert outcome.code == "query_plan_invalid"
    assert llm.text_calls == []  # sql_generator.generate_sql()이 호출되지 않았다.
    assert mcp.execute_readonly_query_calls == []


async def test_query_plan_semantic_violation_maps_to_rejected():
    bad_plan = {**_QUERY_PLAN, "depth": 2}
    llm = FakeLLMClient(json_responses=[_RUNTIME_INTENT, bad_plan])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-7",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.RejectedOutcome)
    assert outcome.code == "query_plan_invalid"
    assert mcp.execute_readonly_query_calls == []


async def test_sql_rejected_maps_to_rejected():
    bad_sql = _GOOD_SQL.replace("AS CurrentInventory", "AS TotalStock")
    llm = FakeLLMClient(json_responses=[_RUNTIME_INTENT, _QUERY_PLAN], text_responses=[bad_sql])
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-8",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.RejectedOutcome)
    assert outcome.code == "sql_rejected"
    assert mcp.execute_readonly_query_calls == []


@pytest.mark.parametrize("exc", [MCPToolExecutionError("boom", reason="tool_error"), MCPTransportError("boom", reason="call_timeout")])
async def test_mcp_execution_failure_maps_to_failed(exc):
    llm = _happy_llm()
    mcp = FakeMCPClientManager(execute_error=exc)
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-9",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.FailedOutcome)
    assert outcome.code == "mcp_execution_failed"


async def test_unexpected_exception_maps_to_internal_error():
    llm = FakeLLMClient(fail_with=RuntimeError("totally unexpected bug"))
    mcp = FakeMCPClientManager()
    outcome = await agent_service.handle_question(
        question="질문",
        correlation_id="corr-10",
        llm_client=llm,
        mcp_client_manager=mcp,
        physical_metadata_catalog=_CATALOG,
    )
    assert isinstance(outcome, agent_service.FailedOutcome)
    assert outcome.code == "internal_error"
    assert "totally unexpected bug" not in outcome.message


def test_outcome_models_reject_extra_fields():
    with pytest.raises(Exception):
        agent_service.RejectedOutcome(
            correlation_id="x", code="invalid_request", message="m", extra="nope"
        )


def test_outcome_models_reject_unknown_code():
    with pytest.raises(Exception):
        agent_service.RejectedOutcome(correlation_id="x", code="not_a_real_code", message="m")


def test_outcome_models_reject_blank_message():
    with pytest.raises(Exception):
        agent_service.RejectedOutcome(correlation_id="x", code="invalid_request", message="   ")


def test_completed_outcome_has_no_code_or_message_fields():
    assert "code" not in agent_service.CompletedOutcome.model_fields
    assert "message" not in agent_service.CompletedOutcome.model_fields
