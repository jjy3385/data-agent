"""requires_target_db + requires_llm 둘 다 필요: 실제 Docker AdventureWorks2022와 `.env`에
설정된 실제 LLM Provider를 사용해 대표 질문과 한국어 표현 3종을 전체 파이프라인
(RuntimeIntent -> Metadata Context -> QueryPlan -> SQL -> FEAT-0003 MCP 실행)으로 실행하고
Golden Query 기준과 비교한다.

Golden SQL은 사람이 검토해 이 파일에 고정하지만, 그 결과는 하드코딩하지 않고 테스트
실행마다 `execute_readonly_query` MCP Tool로 새로 조회한다. 이 파일의 어떤 코드도
`pyodbc`로 대상 DB에 직접 연결하지 않으며, API Key나 TARGET_DB_* 값을 출력하거나 assert
메시지에 포함하지 않는다.
"""

import pytest

from app.mcp.lifecycle import mcp_lifespan
from app.services import agent_service
from app.services.llm_client import OpenAICompatibleLLMClient

pytestmark = [pytest.mark.requires_target_db, pytest.mark.requires_llm, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


_GOLDEN_SQL = (
    "SELECT p.ProductID, p.Name, SUM(pi.Quantity) AS CurrentInventory, p.SafetyStockLevel\n"
    "FROM Production.Product AS p\n"
    "INNER JOIN Production.ProductInventory AS pi ON p.ProductID = pi.ProductID\n"
    "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n"
    "HAVING SUM(pi.Quantity) < p.SafetyStockLevel\n"
    "ORDER BY p.ProductID"
)

_QUESTIONS = [
    "현재 재고가 안전재고보다 부족한 제품을 보여줘.",
    "안전재고 기준에 미달한 품목을 알려줘.",
    "창고별 수량을 합쳤을 때 최소 재고보다 적은 상품은?",
]

_COMPARABLE_FIELDS = ("ProductID", "Name", "CurrentInventory", "SafetyStockLevel")


def _extract_comparable_rows(columns: list[str], rows: list[list]) -> list[tuple]:
    """columns에서 ProductID/Name/CurrentInventory/SafetyStockLevel 네 컬럼의 위치를 이름으로
    찾아 그 순서의 Tuple 목록으로 정규화한다. 필요한 컬럼이 없으면 명확하게 실패한다."""
    missing = [name for name in _COMPARABLE_FIELDS if name not in columns]
    assert not missing, f"필요한 컬럼이 결과에 없습니다: {missing} (실제 columns={columns})"
    indexes = [columns.index(name) for name in _COMPARABLE_FIELDS]
    return [tuple(row[i] for i in indexes) for row in rows]


@pytest.mark.parametrize("question", _QUESTIONS)
async def test_representative_and_korean_variants_match_golden_query(question):
    llm_client = OpenAICompatibleLLMClient()
    try:
        async with mcp_lifespan() as manager:
            golden = await manager.execute_readonly_query(
                sql=_GOLDEN_SQL,
                parameters=[],
                correlation_id="golden-query",
                query_timeout_seconds=10,
                maximum_returned_rows=500,
            )
            assert not golden["truncated"], "Golden Query 결과가 잘렸습니다 — maximum_returned_rows를 늘려야 합니다."

            outcome = await agent_service.handle_question(
                question=question,
                correlation_id="e2e-golden-comparison",
                llm_client=llm_client,
                mcp_client_manager=manager,
                physical_metadata_catalog=None,
            )
    finally:
        await llm_client.aclose()

    assert outcome.status == "completed", (
        f"status={outcome.status!r}, code={getattr(outcome, 'code', None)!r}, "
        f"message={getattr(outcome, 'message', None)!r}"
    )

    # ProductID/Name/CurrentInventory/SafetyStockLevel 네 필드 모두 이름으로 컬럼 위치를 찾아
    # ProductID 오름차순이 유지된 전체 목록을 비교한다(생성 SQL 문자열 자체는 비교하지 않는다).
    golden_rows = _extract_comparable_rows(golden["columns"], golden["rows"])
    pipeline_rows = _extract_comparable_rows(outcome.bounded_result.columns, outcome.bounded_result.rows)

    assert pipeline_rows == golden_rows, (
        "제품 집합·ProductID 정렬 순서·Name·CurrentInventory·SafetyStockLevel 중 하나 이상이 "
        "Golden Query와 다릅니다."
    )
