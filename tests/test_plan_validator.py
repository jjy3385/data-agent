import pytest

from app.services import context_builder, metadata_service
from app.services.plan_validator import QueryPlanInvalidError, validate
from app.services.query_planner import QueryPlan

_CONTEXT = context_builder.build(metadata_service.all_entries())

_VALID_PLAN_KWARGS = dict(
    purpose="안전재고보다 현재 재고가 부족한 제품을 조회한다",
    entity_id="product",
    dimension_ids=["product_id", "product_name"],
    metric_ids=["current_inventory", "safety_stock_level"],
    filters=[{"filter_id": "below_safety_stock", "parameters": {}}],
    time_policy_id=None,
    grain_id="product",
    join_ids=["product_to_product_inventory"],
    order_by=[{"field_id": "product_id", "direction": "asc"}],
    limit=100,
    depth=1,
)


def _plan(**overrides) -> QueryPlan:
    kwargs = {**_VALID_PLAN_KWARGS, **overrides}
    return QueryPlan.model_validate(kwargs)


def test_validate_accepts_representative_plan():
    plan = _plan()
    assert validate(plan, _CONTEXT) is plan


def test_validate_rejects_unknown_metadata_id():
    plan = _plan(metric_ids=["current_inventory", "sales_amount"])
    with pytest.raises(QueryPlanInvalidError, match="sales_amount"):
        validate(plan, _CONTEXT)


def test_validate_rejects_depth_other_than_1():
    plan = _plan(depth=2)
    with pytest.raises(QueryPlanInvalidError, match="depth"):
        validate(plan, _CONTEXT)


def test_validate_rejects_grain_id_of_wrong_kind():
    # 레지스트리의 grain kind에는 "product" 하나만 있으므로, 다른 kind의 id를 grain_id로
    # 쓰면 종류별 검증(Codex 발견 2)이 "grain_id는 product여야 한다"는 값 검증보다 먼저
    # 걸린다 — 이 자체가 고정 Demo Scope 밖 값을 막는 의도된 동작이다.
    plan = _plan(grain_id="current_inventory")
    with pytest.raises(QueryPlanInvalidError, match="grain Metadata Context group"):
        validate(plan, _CONTEXT)


def test_validate_rejects_missing_display_dimensions():
    plan = _plan(dimension_ids=["product_id"])
    with pytest.raises(QueryPlanInvalidError, match="product_name"):
        validate(plan, _CONTEXT)


def test_validate_rejects_wrong_first_order_by():
    plan = _plan(order_by=[{"field_id": "safety_stock_level", "direction": "asc"}])
    with pytest.raises(QueryPlanInvalidError, match="order_by"):
        validate(plan, _CONTEXT)


def test_validate_rejects_limit_above_maximum():
    plan = _plan(limit=1000)
    with pytest.raises(QueryPlanInvalidError, match="limit"):
        validate(plan, _CONTEXT)


# --- Codex 발견 1: 고정 Demo Scope 필수 Filter·Metric·Join·Entity 의미 강제 -----------------


def test_validate_rejects_empty_filters():
    plan = _plan(filters=[])
    with pytest.raises(QueryPlanInvalidError, match="below_safety_stock"):
        validate(plan, _CONTEXT)


def test_validate_rejects_missing_below_safety_stock_filter():
    # 존재하지만 다른 kind가 아니라, 아예 등록되지 않은 filter_id를 쓰면 종류별 검증이 먼저
    # 걸린다. below_safety_stock 하나만 등록되어 있어 "다른 유효한 filter"를 만들 수 없으므로
    # 빈 filters 케이스와 별개로 "필수 filter 자체가 없다"는 경로를 구조적으로 위반한
    # QueryPlan으로 확인한다.
    plan = _plan(filters=[{"filter_id": "below_safety_stock", "parameters": {"threshold": 1}}])
    with pytest.raises(QueryPlanInvalidError, match="parameters must be empty"):
        validate(plan, _CONTEXT)


@pytest.mark.parametrize("required_metric", ["current_inventory", "safety_stock_level"])
def test_validate_rejects_missing_required_metric(required_metric):
    remaining = [m for m in _VALID_PLAN_KWARGS["metric_ids"] if m != required_metric]
    plan = _plan(metric_ids=remaining)
    with pytest.raises(QueryPlanInvalidError, match="metric_ids must include"):
        validate(plan, _CONTEXT)


def test_validate_rejects_missing_required_join():
    plan = _plan(join_ids=[])
    with pytest.raises(QueryPlanInvalidError, match="join_ids must include"):
        validate(plan, _CONTEXT)


def test_validate_rejects_non_null_time_policy_id():
    # time_policy_id로 쓸 수 있는 승인된 Time Policy가 이 Demo Scope에는 없으므로, 존재하지
    # 않는 임의 값도 결과적으로 같은 요구사항(반드시 null)을 위반한 것으로 거부된다.
    plan = _plan(time_policy_id="fiscal_quarter")
    with pytest.raises(QueryPlanInvalidError, match="time_policy_id must be null"):
        validate(plan, _CONTEXT)


def test_validate_rejects_dimension_id_outside_demo_scope():
    # 레지스트리에 등록되지 않은 임의 Dimension은 종류별 검증에서 거부된다(Demo Scope 밖).
    plan = _plan(dimension_ids=["product_id", "product_name", "unregistered_dimension"])
    with pytest.raises(QueryPlanInvalidError, match="dimension Metadata Context group"):
        validate(plan, _CONTEXT)


# --- Codex 발견 2: Metadata ID 종류별 검증 ---------------------------------------------------
# entity_id는 레지스트리에 "product" 하나만 있어 "잘못된 값"과 "잘못된 종류"가 같은 입력으로
# 밖에 표현되지 않으므로, Metric ID를 entity_id로 쓰는 이 테스트 하나가 발견 1의 "entity_id는
# product여야 한다"와 발견 2의 "종류가 다른 ID 거부"를 함께 검증한다.
def test_validate_rejects_metric_id_used_as_entity_id():
    plan = _plan(entity_id="current_inventory")
    with pytest.raises(QueryPlanInvalidError, match="entity Metadata Context group"):
        validate(plan, _CONTEXT)


def test_validate_rejects_join_id_used_as_dimension_id():
    plan = _plan(dimension_ids=["product_id", "product_name", "product_to_product_inventory"])
    with pytest.raises(QueryPlanInvalidError, match="dimension Metadata Context group"):
        validate(plan, _CONTEXT)


def test_validate_rejects_filter_id_used_as_metric_id():
    plan = _plan(metric_ids=["current_inventory", "safety_stock_level", "below_safety_stock"])
    with pytest.raises(QueryPlanInvalidError, match="metric Metadata Context group"):
        validate(plan, _CONTEXT)


def test_validate_rejects_metric_id_used_as_join_id():
    plan = _plan(join_ids=["product_to_product_inventory", "current_inventory"])
    with pytest.raises(QueryPlanInvalidError, match="join Metadata Context group"):
        validate(plan, _CONTEXT)


def test_validate_rejects_metric_id_used_as_filter_id():
    plan = _plan(
        filters=[
            {"filter_id": "below_safety_stock", "parameters": {}},
            {"filter_id": "current_inventory", "parameters": {}},
        ]
    )
    with pytest.raises(QueryPlanInvalidError, match="filter Metadata Context group"):
        validate(plan, _CONTEXT)
