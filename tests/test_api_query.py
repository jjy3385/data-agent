from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api import query
from app.services.agent_service import BoundedResult, CompletedOutcome
from main import app as main_app
from tests.conftest import FakeLLMClient

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


def test_extra_field_is_rejected(admin_db_path):
    with TestClient(main_app) as client:
        response = client.post("/api/questions", json={"question": "재고 알려줘", "sql": "SELECT 1"})
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "rejected"
    assert body["code"] == "invalid_request"
    assert body["correlation_id"]


def test_blank_question_is_rejected(admin_db_path):
    with TestClient(main_app) as client:
        response = client.post("/api/questions", json={"question": "   "})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_missing_question_is_rejected(admin_db_path):
    with TestClient(main_app) as client:
        response = client.post("/api/questions", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_non_string_question_is_rejected(admin_db_path):
    with TestClient(main_app) as client:
        response = client.post("/api/questions", json={"question": 123})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_non_object_body_is_rejected(admin_db_path):
    with TestClient(main_app) as client:
        response = client.post("/api/questions", json=["not", "an", "object"])
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_malformed_json_body_is_rejected(admin_db_path):
    with TestClient(main_app) as client:
        response = client.post(
            "/api/questions",
            content=b"{not valid json",
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_validation_handler_does_not_affect_other_routes():
    """/api/questions 밖의 경로는 FastAPI 기본 검증 오류 형식을 그대로 유지한다."""

    class Body(BaseModel):
        value: int

    other_app = FastAPI()
    other_app.include_router(query.router)

    @other_app.post("/other")
    async def other_route(body: Body) -> dict:
        return {"value": body.value}

    other_app.add_exception_handler(RequestValidationError, query.validation_exception_handler)

    with TestClient(other_app) as client:
        response = client.post("/other", json={"value": "not-an-int"})

    assert response.status_code == 422
    body = response.json()
    # FastAPI 기본 형식은 "detail" 키를 사용하며 자연어 질문 Contract 형식(status/code)이 아니다.
    assert "detail" in body
    assert "status" not in body


def test_happy_path_returns_completed_with_bounded_result(admin_db_path):
    fake_llm = FakeLLMClient(json_responses=[_RUNTIME_INTENT, _QUERY_PLAN], text_responses=[_GOOD_SQL])
    main_app.dependency_overrides[query.get_llm_client] = lambda: fake_llm
    try:
        with TestClient(main_app) as client:
            response = client.post(
                "/api/questions", json={"question": "현재 재고가 안전재고보다 부족한 제품을 보여줘"}
            )
    finally:
        main_app.dependency_overrides.pop(query.get_llm_client, None)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "bounded_result" in body
    assert body["correlation_id"]


def test_outcome_response_status_code_mapping():
    outcome = CompletedOutcome(
        correlation_id="x",
        bounded_result=BoundedResult(columns=["ProductID"], rows=[[1]], row_count=1, truncated=False, execution_ms=1),
    )
    response = query._outcome_response(outcome)
    assert response.status_code == 200
