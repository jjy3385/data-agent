"""검증된 RuntimeIntent와 Metadata Context -> QueryPlan 생성.

QueryPlan Contract(docs/contracts/query-plan.md)의 구조·타입·Enum·중복 금지 규칙만
여기서 구현한다(구조적 검증). Metadata Context 참조 존재 여부, Demo Scope, depth,
grain_id, order_by, limit 같은 Backend 의미 검증은 plan_validator.py가 담당한다.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.services.context_builder import MetadataContext
from app.services.intent_resolver import RuntimeIntent
from app.services.llm_client import LLMClient

_MAX_COMPLETION_TOKENS = 3000

_SYSTEM_PROMPT = """당신은 검증된 RuntimeIntent와 승인된 Metadata Context만 사용해
QueryPlan JSON을 만드는 역할만 담당한다. 다음 JSON 스키마를 정확히 만족하는 JSON 객체
하나만 출력한다. 다른 텍스트를 출력하지 않는다.

{
  "purpose": "이 조회의 목적을 설명하는 문장",
  "entity_id": "Metadata Context의 entities 중 하나의 id",
  "dimension_ids": ["Metadata Context의 dimensions id 목록"],
  "metric_ids": ["Metadata Context의 metrics id 목록, 최소 1개"],
  "filters": [{"filter_id": "Metadata Context의 filters id", "parameters": {}}],
  "time_policy_id": null,
  "grain_id": "Metadata Context의 grains 중 하나의 id",
  "join_ids": ["Metadata Context의 joins id 목록"],
  "order_by": [{"field_id": "dimension_ids 또는 metric_ids에 있는 id", "direction": "asc"}],
  "limit": 100,
  "depth": 1
}

규칙:
- Metadata Context에 없는 id를 만들어내지 않는다.
- dimension_ids에는 결과에 표시할 제품 식별자(product_id)와 표시명(product_name)을 반드시
  포함한다.
- grain_id는 반드시 "product"다. depth는 반드시 1이다.
- order_by의 첫 번째 항목은 반드시 {"field_id": "product_id", "direction": "asc"}다.
- limit은 1 이상 100 이하의 정수다.
- filters[].parameters는 원시 값(문자열/숫자/불리언)만 담고 중첩 객체나 배열을 넣지 않는다.
- Metadata Context의 filters 목록에 있는 항목은 그 description이 질문의 조건과 일치하면
  반드시 filters 배열에 포함해야 한다. 예를 들어 질문이 "재고가 안전재고보다 부족한
  제품"을 찾는 것이면 안전재고 부족을 뜻하는 filter를 filters 배열에서 빠뜨리지 않는다.
  질문이 요구하는 조건을 표현하는 filter가 있는데도 filters를 빈 배열로 두지 않는다.
"""


class QueryPlanFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filter_id: str
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("filter_id")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("filter_id must not be blank")
        return value


class QueryPlanOrderBy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_id: str
    direction: Literal["asc", "desc"]

    @field_validator("field_id")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field_id must not be blank")
        return value


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str
    entity_id: str
    dimension_ids: list[str]
    metric_ids: list[str]
    filters: list[QueryPlanFilter]
    time_policy_id: str | None
    grain_id: str
    join_ids: list[str]
    order_by: list[QueryPlanOrderBy]
    limit: int
    depth: int

    @model_validator(mode="after")
    def _check_invariants(self) -> "QueryPlan":
        for field_name, value in (
            ("purpose", self.purpose),
            ("entity_id", self.entity_id),
            ("grain_id", self.grain_id),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")

        for field_name, values in (
            ("dimension_ids", self.dimension_ids),
            ("metric_ids", self.metric_ids),
            ("join_ids", self.join_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicate ids")

        if not self.metric_ids:
            raise ValueError("metric_ids must contain at least 1 entry")

        filter_ids = [f.filter_id for f in self.filters]
        if len(filter_ids) != len(set(filter_ids)):
            raise ValueError("filters must not contain duplicate filter_id")

        if not self.order_by:
            raise ValueError("order_by must contain at least 1 entry")
        order_field_ids = [o.field_id for o in self.order_by]
        if len(order_field_ids) != len(set(order_field_ids)):
            raise ValueError("order_by must not contain duplicate field_id")

        allowed_order_fields = set(self.dimension_ids) | set(self.metric_ids)
        for order_entry in self.order_by:
            if order_entry.field_id not in allowed_order_fields:
                raise ValueError(
                    f"order_by field_id {order_entry.field_id!r} must be in dimension_ids or metric_ids"
                )

        if self.limit < 1:
            raise ValueError("limit must be >= 1")

        return self


class QueryPlanInvalidError(RuntimeError):
    """LLM이 생성한 값이 QueryPlan Contract 구조를 만족하지 않을 때 발생한다."""


async def generate_query_plan(
    intent: RuntimeIntent, context: MetadataContext, llm_client: LLMClient
) -> QueryPlan:
    """LLM을 호출해 QueryPlan Contract 구조를 만족하는 QueryPlan을 반환한다.

    Backend 의미 검증(Metadata Context 참조 존재, Demo Scope 등)은 plan_validator.validate()가
    이어서 수행한다. 여기서는 구조적 Contract 위반만 QueryPlanInvalidError로 변환한다.
    """
    user_prompt = json.dumps(
        {
            "runtime_intent": intent.model_dump(),
            "metadata_context": context.as_prompt_dict(),
        },
        ensure_ascii=False,
    )

    raw: dict[str, Any]
    try:
        raw = await llm_client.complete_json(
            _SYSTEM_PROMPT, user_prompt, max_completion_tokens=_MAX_COMPLETION_TOKENS
        )
    except json.JSONDecodeError as exc:
        raise QueryPlanInvalidError("LLM response is not valid JSON") from exc

    try:
        return QueryPlan.model_validate(raw)
    except ValidationError as exc:
        raise QueryPlanInvalidError("QueryPlan Contract violation") from exc
