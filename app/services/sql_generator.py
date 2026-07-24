"""검증된 QueryPlan과 제한된 Metadata Context -> MSSQL SELECT 문자열 생성.

이 모듈은 항상 LLM을 호출한다. 질문이나 QueryPlan을 고정 SQL에 매핑하는 코드 경로를
만들지 않는다(NFR-003). 생성된 SQL은 sql_guardrail.validate()가 실행 전 최소 검증한다.
"""

from __future__ import annotations

from app.services.context_builder import MetadataContext
from app.services.llm_client import LLMClient
from app.services.query_planner import QueryPlan

_MAX_COMPLETION_TOKENS = 2000

_SYSTEM_PROMPT = """당신은 검증된 QueryPlan과 제한된 Metadata Context만 사용해 단일 MSSQL
SELECT Statement를 생성하는 역할만 담당한다. SQL 코드만 출력하고 다른 설명이나 Markdown
코드 Fence를 포함하지 않는다.

반드시 지켜야 하는 규칙:
- SELECT로 시작하는 단일 SELECT Statement 하나만 작성한다(세미콜론, 주석, 다중 Statement,
  Subquery, UNION 금지).
- SELECT 바로 뒤에 TOP (N)을 명시한다. N은 QueryPlan의 limit 값을 그대로 사용한다.
- SELECT 목록에 '*'를 사용하지 않고 필요한 Column을 각각 명시한다.
- 문자열 Literal(홑따옴표)을 사용하지 않는다.
- FROM/JOIN에서 참조하는 모든 Table은 반드시 AS로 별칭을 선언한다(암묵적 별칭 금지).
- 출력 Column에는 반드시 AS로 다음 네 이름 중 하나만 사용한다: ProductID, Name,
  CurrentInventory, SafetyStockLevel. 이 네 이름 밖의 출력 별칭을 만들지 않는다.
- Metadata Context의 sql_hint에 있는 물리 Table·Column·집계·Join·Filter 표현만 사용하고
  다른 Table이나 Column을 새로 참조하지 않는다.
- ORDER BY의 첫 번째 정렬 기준은 반드시 ProductID ASC다.
"""


async def generate_sql(plan: QueryPlan, context: MetadataContext, llm_client: LLMClient) -> str:
    user_prompt = _build_user_prompt(plan, context)
    text = await llm_client.complete_text(
        _SYSTEM_PROMPT, user_prompt, max_completion_tokens=_MAX_COMPLETION_TOKENS
    )
    return _extract_sql(text)


def _build_user_prompt(plan: QueryPlan, context: MetadataContext) -> str:
    import json

    return json.dumps(
        {
            "query_plan": plan.model_dump(),
            "metadata_context": context.as_prompt_dict(),
        },
        ensure_ascii=False,
    )


def _extract_sql(text: str) -> str:
    """LLM 응답에서 Markdown 코드 Fence가 있으면 벗겨내고 SQL 문자열만 남긴다."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped
