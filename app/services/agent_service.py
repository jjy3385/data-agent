"""Workflow Orchestrator: Correlation ID 사용, 단계별 호출 순서, 예외 -> Contract 응답 매핑.

RuntimeIntent -> Metadata Context -> QueryPlan -> SQL -> MCP 실행 순서로 각 단계를 호출하고,
각 단계의 예외를 자연어 질문 API Contract의 status/code로 변환한다. 이 함수는 예외를
Router 밖으로 전파하지 않는다.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.mcp.client_manager import MCPClientManager, MCPToolExecutionError, MCPTransportError
from app.services import context_builder, metadata_retriever, query_planner, sql_generator, sql_guardrail
from app.services.intent_resolver import IntentContractViolationError, generate_runtime_intent
from app.services.llm_client import LLMClient, LLMUnavailableError
from app.services.metadata_retriever import MetadataNotFoundError
from app.services.plan_validator import QueryPlanInvalidError
from app.services.plan_validator import validate as validate_query_plan
from app.services.schema_collector import PhysicalMetadataCatalog
from app.services.sql_guardrail import SqlRejectedError

logger = logging.getLogger(__name__)

QUERY_TIMEOUT_SECONDS = 10
MAXIMUM_RETURNED_ROWS = 100

_RATE_LIMITED_MESSAGE = "LLM 사용 한도를 초과했거나 일시적으로 요청이 제한되었습니다. 잠시 후 다시 시도해 주세요."
_LLM_UNAVAILABLE_MESSAGE = "설정된 LLM Provider를 사용할 수 없습니다."


def _llm_unavailable_message(exc: LLMUnavailableError) -> str:
    """공개 code는 항상 llm_unavailable로 유지하되, Rate Limit일 때만 사용자에게 재시도를
    안내하는 메시지를 쓴다. Provider 원문 오류·reason 값 자체는 응답에 노출하지 않는다."""
    if exc.reason == "rate_limited":
        return _RATE_LIMITED_MESSAGE
    return _LLM_UNAVAILABLE_MESSAGE

_RejectedCode = Literal[
    "invalid_request",
    "intent_contract_violation",
    "metadata_not_found",
    "query_plan_invalid",
    "sql_rejected",
]
_FailedCode = Literal["llm_unavailable", "mcp_execution_failed", "internal_error"]


def _non_blank_message(value: str) -> str:
    if not value.strip():
        raise ValueError("message must not be blank")
    return value


class BoundedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_ms: int


class CompletedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    status: Literal["completed"] = "completed"
    bounded_result: BoundedResult


class ClarificationRequiredOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    status: Literal["clarification_required"] = "clarification_required"
    code: Literal["clarification_required"] = "clarification_required"
    message: str

    @field_validator("message")
    @classmethod
    def _message_non_blank(cls, value: str) -> str:
        return _non_blank_message(value)


class RejectedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    status: Literal["rejected"] = "rejected"
    code: _RejectedCode
    message: str

    @field_validator("message")
    @classmethod
    def _message_non_blank(cls, value: str) -> str:
        return _non_blank_message(value)


class FailedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    status: Literal["failed"] = "failed"
    code: _FailedCode
    message: str

    @field_validator("message")
    @classmethod
    def _message_non_blank(cls, value: str) -> str:
        return _non_blank_message(value)


QuestionOutcome = Annotated[
    CompletedOutcome | ClarificationRequiredOutcome | RejectedOutcome | FailedOutcome,
    Field(discriminator="status"),
]


async def handle_question(
    question: str,
    correlation_id: str,
    llm_client: LLMClient,
    mcp_client_manager: MCPClientManager,
    physical_metadata_catalog: PhysicalMetadataCatalog,
) -> QuestionOutcome:
    """예외를 상위로 전파하지 않는다 — 분류되지 않은 예외도 이 함수 안에서 internal_error로 변환한다."""
    try:
        return await _handle_question(
            question, correlation_id, llm_client, mcp_client_manager, physical_metadata_catalog
        )
    except Exception:
        logger.exception(
            "Unexpected internal error while handling question", extra={"correlation_id": correlation_id}
        )
        return FailedOutcome(
            correlation_id=correlation_id,
            code="internal_error",
            message="예상하지 못한 내부 오류가 발생했습니다.",
        )


async def _handle_question(
    question: str,
    correlation_id: str,
    llm_client: LLMClient,
    mcp_client_manager: MCPClientManager,
    physical_metadata_catalog: PhysicalMetadataCatalog,
) -> QuestionOutcome:
    # physical_metadata_catalog는 Startup 시 validate_physical_mapping()이 이미 검증했다.
    # 요청 처리 단계에서는 Business Metadata(metadata_service의 정적 레지스트리)만 사용한다.
    _ = physical_metadata_catalog

    try:
        intent = await generate_runtime_intent(question, llm_client)
    except LLMUnavailableError as exc:
        return FailedOutcome(
            correlation_id=correlation_id,
            code="llm_unavailable",
            message=_llm_unavailable_message(exc),
        )
    except IntentContractViolationError:
        return RejectedOutcome(
            correlation_id=correlation_id,
            code="intent_contract_violation",
            message="자연어 질문을 구조화된 형태로 이해하지 못했습니다.",
        )

    if intent.requires_clarification:
        return ClarificationRequiredOutcome(
            correlation_id=correlation_id,
            message=intent.clarification_reason or "질문을 더 구체적으로 알려주세요.",
        )

    try:
        entries = metadata_retriever.retrieve(intent)
    except MetadataNotFoundError:
        return RejectedOutcome(
            correlation_id=correlation_id,
            code="metadata_not_found",
            message="이 질문에 필요한 정보를 현재 지원 범위에서 찾을 수 없습니다.",
        )

    context = context_builder.build(entries)

    try:
        plan = await query_planner.generate_query_plan(intent, context, llm_client)
    except LLMUnavailableError as exc:
        return FailedOutcome(
            correlation_id=correlation_id,
            code="llm_unavailable",
            message=_llm_unavailable_message(exc),
        )
    except QueryPlanInvalidError:
        return RejectedOutcome(
            correlation_id=correlation_id,
            code="query_plan_invalid",
            message="조회 계획을 검증하지 못했습니다.",
        )

    try:
        plan = validate_query_plan(plan, context)
    except QueryPlanInvalidError:
        return RejectedOutcome(
            correlation_id=correlation_id,
            code="query_plan_invalid",
            message="조회 계획을 검증하지 못했습니다.",
        )

    try:
        sql = await sql_generator.generate_sql(plan, context, llm_client)
    except LLMUnavailableError as exc:
        return FailedOutcome(
            correlation_id=correlation_id,
            code="llm_unavailable",
            message=_llm_unavailable_message(exc),
        )

    try:
        sql = sql_guardrail.validate(sql, context)
    except SqlRejectedError:
        return RejectedOutcome(
            correlation_id=correlation_id,
            code="sql_rejected",
            message="생성된 조회문이 실행 제한을 통과하지 못했습니다.",
        )

    try:
        result = await mcp_client_manager.execute_readonly_query(
            sql=sql,
            parameters=[],
            correlation_id=correlation_id,
            query_timeout_seconds=QUERY_TIMEOUT_SECONDS,
            maximum_returned_rows=MAXIMUM_RETURNED_ROWS,
        )
    except (MCPToolExecutionError, MCPTransportError):
        return FailedOutcome(
            correlation_id=correlation_id,
            code="mcp_execution_failed",
            message="조회를 실행하지 못했습니다.",
        )

    bounded_result = BoundedResult(
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
        truncated=result["truncated"],
        execution_ms=result["execution_ms"],
    )
    return CompletedOutcome(correlation_id=correlation_id, bounded_result=bounded_result)
