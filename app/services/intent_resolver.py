"""자연어 질문 -> RuntimeIntent 생성과 RuntimeIntent Contract 검증.

RuntimeIntent Contract(docs/contracts/runtime-intent.md)의 7개 필드, Enum과 조건부
불변조건을 그대로 구현한다. LLM 산출물은 이 검증을 통과한 뒤에만 다음 단계로 전달된다.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.services.llm_client import LLMClient

_MAX_COMPLETION_TOKENS = 2000

_SYSTEM_PROMPT = """당신은 자연어 질문을 RuntimeIntent JSON으로 구조화하는 역할만 담당한다.
다음 JSON 스키마를 정확히 만족하는 JSON 객체 하나만 출력한다. 다른 텍스트를 출력하지 않는다.

{
  "request_type": "lookup" | "aggregation" | "comparison" | "ranking" | "complex_investigation",
  "subject": "질문의 중심 Entity 후보(예: product)",
  "requested_concepts": ["질문에서 추출한 검색어 목록"],
  "requested_output": "list" | "summary" | "ranking" | "investigation",
  "explicit_parameters": {},
  "requires_clarification": false,
  "clarification_reason": null
}

규칙:
- 실제 SQL, 업무 공식, 기간 정책, Join을 스스로 결정하지 않는다. requested_concepts는 검색
  입력일 뿐 승인된 Metadata ID가 아니다.
- explicit_parameters는 사용자가 직접 말한 원시 값만 담고(문자열/숫자/불리언), 중첩 객체나
  배열을 넣지 않는다. 값이 없으면 빈 객체 {}로 둔다.
- requires_clarification이 true이면 clarification_reason에 비어 있지 않은 이유를 적고
  subject/requested_concepts는 비어 있어도 된다.
- requires_clarification이 false이면 clarification_reason은 반드시 null이고
  requested_concepts는 최소 1개 이상이어야 한다.
- 질문이 재고와 안전재고 비교처럼 명확하면 명확화를 요청하지 않는다.
- subject는 제품에 대한 질문이면 정확히 "product"로 적는다("품목", "상품" 등으로 바꾸지 않는다).
- requested_concepts에서 개념을 표현할 때는 아래 표준 용어를 그대로 사용하고 다른 동의어로
  바꾸지 않는다. 질문이 재고(창고 수량 합계, 보유량 등 포함) 개념을 다루면 반드시
  "재고"라는 단어를 그대로 포함한다. 질문이 안전재고 기준(최소 기준, 미달 여부 포함)을
  다루면 반드시 "안전재고"라는 단어를 그대로 포함한다. 예: "현재 재고가 안전재고보다
  부족한 제품을 보여줘" -> requested_concepts: ["재고", "안전재고"].
"""


class IntentContractViolationError(RuntimeError):
    """LLM이 생성한 값이 RuntimeIntent Contract를 만족하지 않을 때 발생한다."""


class RuntimeIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: Literal["lookup", "aggregation", "comparison", "ranking", "complex_investigation"]
    subject: str
    requested_concepts: list[str]
    requested_output: Literal["list", "summary", "ranking", "investigation"]
    explicit_parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    requires_clarification: bool
    clarification_reason: str | None

    @model_validator(mode="after")
    def _check_invariants(self) -> "RuntimeIntent":
        if self.requires_clarification:
            if self.clarification_reason is None or not self.clarification_reason.strip():
                raise ValueError(
                    "clarification_reason must be a non-blank string when requires_clarification is true"
                )
        else:
            if self.clarification_reason is not None:
                raise ValueError("clarification_reason must be null when requires_clarification is false")
            if not self.requested_concepts:
                raise ValueError("requested_concepts must not be empty when requires_clarification is false")
            if not self.subject.strip():
                raise ValueError("subject must not be blank when requires_clarification is false")
        return self


async def generate_runtime_intent(question: str, llm_client: LLMClient) -> RuntimeIntent:
    """LLM을 호출해 RuntimeIntent Contract를 만족하는 RuntimeIntent를 반환한다.

    LLM 호출 자체의 실패는 llm_client가 LLMUnavailableError로 던진다(그대로 전파).
    응답이 유효한 JSON이 아니거나 Contract를 위반하면 IntentContractViolationError.
    """
    raw: dict[str, Any]
    try:
        raw = await llm_client.complete_json(
            _SYSTEM_PROMPT, question, max_completion_tokens=_MAX_COMPLETION_TOKENS
        )
    except json.JSONDecodeError as exc:
        raise IntentContractViolationError("LLM response is not valid JSON") from exc

    try:
        return RuntimeIntent.model_validate(raw)
    except ValidationError as exc:
        raise IntentContractViolationError("RuntimeIntent Contract violation") from exc
