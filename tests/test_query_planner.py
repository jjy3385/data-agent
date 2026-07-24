import pytest

from app.services import context_builder, metadata_service
from app.services.intent_resolver import RuntimeIntent
from app.services.query_planner import QueryPlanInvalidError, generate_query_plan
from tests.conftest import FakeLLMClient

pytestmark = pytest.mark.anyio

_CONTEXT = context_builder.build(metadata_service.all_entries())

_INTENT = RuntimeIntent(
    request_type="lookup",
    subject="product",
    requested_concepts=["inventory", "safety_stock"],
    requested_output="list",
    explicit_parameters={},
    requires_clarification=False,
    clarification_reason=None,
)

_VALID_PLAN = {
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


async def test_generate_query_plan_success():
    fake = FakeLLMClient(json_responses=[_VALID_PLAN])
    plan = await generate_query_plan(_INTENT, _CONTEXT, fake)
    assert plan.entity_id == "product"
    assert plan.depth == 1
    assert fake.json_calls[0][2] == 3000


@pytest.mark.parametrize(
    "broken",
    [
        {**_VALID_PLAN, "extra_field": "nope"},
        {**_VALID_PLAN, "purpose": "   "},
        {**_VALID_PLAN, "metric_ids": []},
        {**_VALID_PLAN, "dimension_ids": ["product_id", "product_id"]},
        {**_VALID_PLAN, "order_by": []},
        {**_VALID_PLAN, "order_by": [{"field_id": "not_in_dims_or_metrics", "direction": "asc"}]},
        {**_VALID_PLAN, "limit": 0},
        {
            **_VALID_PLAN,
            "filters": [
                {"filter_id": "below_safety_stock", "parameters": {}},
                {"filter_id": "below_safety_stock", "parameters": {}},
            ],
        },
    ],
)
async def test_structural_contract_violations_are_rejected(broken):
    fake = FakeLLMClient(json_responses=[broken])
    with pytest.raises(QueryPlanInvalidError):
        await generate_query_plan(_INTENT, _CONTEXT, fake)
