"""QueryPlan Backend 의미 검증(MVP Level 1).

QueryPlan Contract 구조 자체는 query_planner.QueryPlan이 이미 검증했다. 여기서는 두 가지를
확인한다: (1) 각 필드가 QueryPlan Contract가 정의한 종류(Entity/Dimension/Metric/Filter/
Grain/Join)에 맞는 Metadata Context 그룹에서만 참조되는지(종류가 다른 ID는 존재하더라도
거부), (2) FEAT-0004 고정 Demo Scope가 대표 안전재고 질문에 필요하다고 확정한 최소 필수
Filter·Metric·Join·Entity·정렬·Depth·Limit을 실제로 포함하는지. LLM이 Prompt 지시를
따르지 않고 필수 항목을 빠뜨려도(예: `filters=[]`) 이 단계에서 거부된다.
"""

from __future__ import annotations

from app.services.context_builder import MetadataContext
from app.services.metadata_service import MetadataEntry
from app.services.query_planner import QueryPlan, QueryPlanInvalidError

# agent_service.MAXIMUM_RETURNED_ROWS와 동일한 값을 유지한다(순환 Import 회피를 위한 미러링).
_MAXIMUM_RETURNED_ROWS = 100

# FEAT-0004 고정 Demo Scope가 대표 안전재고 질문에 필요하다고 확정한 최소 필수 집합.
# 값은 app/services/metadata_service.py의 레지스트리 id와 반드시 일치해야 한다.
_REQUIRED_ENTITY_ID = "product"
_REQUIRED_GRAIN_ID = "product"
_REQUIRED_DIMENSION_IDS = frozenset({"product_id", "product_name"})
_REQUIRED_METRIC_IDS = frozenset({"current_inventory", "safety_stock_level"})
_REQUIRED_FILTER_ID = "below_safety_stock"
_REQUIRED_JOIN_IDS = frozenset({"product_to_product_inventory"})
_REQUIRED_FIRST_ORDER_BY = ("product_id", "asc")

__all__ = ["QueryPlanInvalidError", "validate"]


def _check_kind(ids: set[str], allowed: dict[str, MetadataEntry], kind_label: str) -> None:
    """id가 존재하기만 하면 통과시키지 않고, 반드시 그 kind에 해당하는 Metadata Context
    그룹(예: metric_ids는 context.metrics)에서만 찾는다. 다른 kind에 존재하는 id는 거부한다."""
    unknown = ids - allowed.keys()
    if unknown:
        raise QueryPlanInvalidError(
            f"QueryPlan references ids outside the {kind_label} Metadata Context group: {sorted(unknown)}"
        )


def validate(plan: QueryPlan, context: MetadataContext) -> QueryPlan:
    # 1) 종류별 검증 — Metadata Context에 존재하기만 하면 통과시키지 않는다(Codex 발견 2).
    _check_kind({plan.entity_id}, context.entities, "entity")
    _check_kind(set(plan.dimension_ids), context.dimensions, "dimension")
    _check_kind(set(plan.metric_ids), context.metrics, "metric")
    _check_kind({f.filter_id for f in plan.filters}, context.filters, "filter")
    _check_kind({plan.grain_id}, context.grains, "grain")
    _check_kind(set(plan.join_ids), context.joins, "join")
    # 현재 FEAT-0004에는 승인된 Time Policy가 하나도 없으므로 null만 허용한다.
    if plan.time_policy_id is not None:
        raise QueryPlanInvalidError(
            "time_policy_id must be null; no Time Policy is registered in this Demo Scope"
        )

    # 2) FEAT-0004 고정 Demo Scope 필수 항목 — 대표 질문에 필요한 최소 구성을 강제한다
    #    (Codex 발견 1). Registry가 각 kind마다 딱 필요한 만큼만 등록되어 있으므로, 위
    #    종류별 검증과 결합하면 이 필수 집합이 곧 허용되는 전체 집합이 되어 Demo Scope
    #    밖의 추가 Dimension·Metric·Filter·Join도 함께 거부된다.
    if plan.entity_id != _REQUIRED_ENTITY_ID:
        raise QueryPlanInvalidError(f'entity_id must be "{_REQUIRED_ENTITY_ID}"')

    if not _REQUIRED_DIMENSION_IDS <= set(plan.dimension_ids):
        raise QueryPlanInvalidError(f"dimension_ids must include {sorted(_REQUIRED_DIMENSION_IDS)}")

    if not _REQUIRED_METRIC_IDS <= set(plan.metric_ids):
        raise QueryPlanInvalidError(f"metric_ids must include {sorted(_REQUIRED_METRIC_IDS)}")

    filters_by_id = {f.filter_id: f for f in plan.filters}
    if _REQUIRED_FILTER_ID not in filters_by_id:
        raise QueryPlanInvalidError(f'filters must include exactly one "{_REQUIRED_FILTER_ID}" filter')
    if filters_by_id[_REQUIRED_FILTER_ID].parameters:
        raise QueryPlanInvalidError(
            f'"{_REQUIRED_FILTER_ID}" filter parameters must be empty in this Demo Scope'
        )

    if not _REQUIRED_JOIN_IDS <= set(plan.join_ids):
        raise QueryPlanInvalidError(f"join_ids must include {sorted(_REQUIRED_JOIN_IDS)}")

    if plan.grain_id != _REQUIRED_GRAIN_ID:
        raise QueryPlanInvalidError(f'grain_id must be "{_REQUIRED_GRAIN_ID}"')

    if plan.depth != 1:
        raise QueryPlanInvalidError("depth must be 1")

    first_order = plan.order_by[0]
    if (first_order.field_id, first_order.direction) != _REQUIRED_FIRST_ORDER_BY:
        raise QueryPlanInvalidError("order_by[0] must be product_id ascending")

    if not (1 <= plan.limit <= _MAXIMUM_RETURNED_ROWS):
        raise QueryPlanInvalidError(f"limit must be between 1 and {_MAXIMUM_RETURNED_ROWS}")

    return plan
