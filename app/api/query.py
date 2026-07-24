"""자연어 질문 API Contract(docs/contracts/natural-language-query.md) 구현.

`/api/questions` 전용 요청/응답 Model과 Validation Handler를 제공한다. 이 Handler는
`/api/questions` 밖의 다른 경로(`/health` 등)에는 영향을 주지 않고 FastAPI 기본 검증
오류 형식을 그대로 위임한다.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.exception_handlers import (
    request_validation_exception_handler as default_request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, field_validator

from app.mcp.client_manager import MCPClientManager
from app.services.agent_service import QuestionOutcome, handle_question
from app.services.llm_client import LLMClient
from app.services.schema_collector import PhysicalMetadataCatalog

router = APIRouter()

_QUESTION_API_PATH = "/api/questions"

_STATUS_TO_HTTP_STATUS_CODE = {
    "completed": 200,
    "clarification_required": 200,
    "rejected": 422,
    "failed": 500,
}


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str

    @field_validator("question")
    @classmethod
    def _question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def get_mcp_client_manager(request: Request) -> MCPClientManager:
    return request.app.state.mcp_client_manager


def get_physical_metadata_catalog(request: Request) -> PhysicalMetadataCatalog:
    return request.app.state.physical_metadata_catalog


def _outcome_response(outcome: QuestionOutcome) -> JSONResponse:
    status_code = _STATUS_TO_HTTP_STATUS_CODE[outcome.status]
    return JSONResponse(status_code=status_code, content=outcome.model_dump())


@router.post(_QUESTION_API_PATH)
async def ask_question(
    payload: QuestionRequest,
    llm_client: LLMClient = Depends(get_llm_client),
    mcp_client_manager: MCPClientManager = Depends(get_mcp_client_manager),
    physical_metadata_catalog: PhysicalMetadataCatalog = Depends(get_physical_metadata_catalog),
) -> JSONResponse:
    correlation_id = str(uuid.uuid4())
    outcome = await handle_question(
        question=payload.question,
        correlation_id=correlation_id,
        llm_client=llm_client,
        mcp_client_manager=mcp_client_manager,
        physical_metadata_catalog=physical_metadata_catalog,
    )
    return _outcome_response(outcome)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    """`/api/questions`의 Body 검증 실패만 rejected/invalid_request Contract 응답으로 변환한다.

    그 외 경로는 FastAPI 기본 RequestValidationError Handler로 위임해 기존 검증 오류 형식을
    그대로 유지한다.
    """
    if request.url.path != _QUESTION_API_PATH:
        return await default_request_validation_exception_handler(request, exc)

    correlation_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=422,
        content={
            "correlation_id": correlation_id,
            "status": "rejected",
            "code": "invalid_request",
            "message": "요청이 자연어 질문 API Contract를 만족하지 않습니다.",
        },
    )
