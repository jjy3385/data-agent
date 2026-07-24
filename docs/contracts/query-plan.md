# 쿼리 계획 계약 (QueryPlan Contract)

> 이 문서는 자연어와 SQL 사이의 검증 가능한 중간 표현인 QueryPlan의 구성요소와 MVP 검증 범위를 정의한다.

## 상태

승인됨 (Accepted). [FEAT-0004 자연어 질문 처리 최소 동작 흐름](../features/0004-natural-language-query-walking-skeleton/spec.md)의 구현 기준으로 사용한다.

## 이 문서를 읽는 이유

* LLM Query Planner가 무엇을 출력해야 하는지 확인한다.
* 각 필드의 타입, 필수 여부와 값의 의미를 확인한다.
* Backend Validator가 어떤 항목을 차단하는지 확인한다.
* MVP Level 1 검증과 Post-MVP 의미 검증의 경계를 구분한다.

## 범위

이 문서는 FEAT-0004 구현에 필요한 최소 수준까지 QueryPlan의 구현 가능한 JSON 구조와 Week 1 Validator 범위를 확정한다. Formula·Aggregation·Grain 의미 검증이나 SQL과의 전체 구조적 일치 확인은 이 문서가 정의하는 Week 1 범위에 포함하지 않는다. SQL 실행 Tool의 형식은 [`execute_readonly_query` Contract](execute-readonly-query.md)에서 정의한다.

## 관련 문서

* [RuntimeIntent Contract](runtime-intent.md)
* [자연어 질문 API Contract](natural-language-query.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP 완료 기준](../mvp/acceptance-criteria.md)
* [FEAT-0004 자연어 질문 처리 최소 동작 흐름 Spec](../features/0004-natural-language-query-walking-skeleton/spec.md)

## 정의

LLM은 QueryPlan에서 Metadata Context에 포함된 관리자 승인 Metadata ID만 참조해야 하며, Backend 검증을 통과한 Plan만 SQL로 변환할 수 있다. 정의되지 않은 추가 필드를 포함하면 Contract를 만족하지 않는 것으로 처리한다.

Metric과 Filter는 서로 다른 Metadata 종류이며 같은 ID 공간으로 혼용하지 않는다. Metric ID는 결과에 표시하거나 계산에 사용하는 값을 가리키고, Filter ID는 승인된 조건(비교·임계값 판정 등)을 가리킨다. `below_safety_stock`처럼 조건 자체를 표현하는 ID는 Filter ID이며 Metric ID로 취급하지 않는다.

## JSON 구조

```json
{
  "purpose": "안전재고보다 현재 재고가 부족한 제품을 조회한다",
  "entity_id": "product",
  "dimension_ids": ["product_id", "product_name"],
  "metric_ids": ["current_inventory", "safety_stock_level"],
  "filters": [
    {
      "filter_id": "below_safety_stock",
      "parameters": {}
    }
  ],
  "time_policy_id": null,
  "grain_id": "product",
  "join_ids": ["product_to_product_inventory"],
  "order_by": [
    {
      "field_id": "product_id",
      "direction": "asc"
    }
  ],
  "limit": 100,
  "depth": 1
}
```

| 필드 | 타입 | 필수 여부 | 의미 |
|---|---|---|---|
| `purpose` | `string` | 필수, trim 후 비어 있지 않음 | 질문을 어떻게 해석했는지 설명하는 실행 목적 |
| `entity_id` | `string` | 필수, trim 후 비어 있지 않음 | 조회와 그룹화의 중심이 되는 승인 Entity Metadata ID |
| `dimension_ids` | `array[string]` | 필수(빈 배열 허용) | 결과에 노출하거나 그룹화 기준으로 사용할 승인 Dimension Metadata ID 목록. 제품 식별자·표시명처럼 결과에 포함해야 하는 필드도 여기에 명시한다 |
| `metric_ids` | `array[string]` | 필수(최소 1개) | 결과에 필요한 승인 Metric Metadata ID 목록 |
| `filters` | `array[object]` | 필수(빈 배열 허용) | 승인 Filter Metadata ID를 참조하는 조건 목록. [`filters[]` 구조](#filters-구조) 참고 |
| `time_policy_id` | `string \| null` | 필수 | 승인된 Time Policy Metadata ID. 시간 개념이 필요 없는 질문에는 `null` |
| `grain_id` | `string` | 필수, trim 후 비어 있지 않음 | 결과 한 행이 의미하는 집계 수준을 가리키는 승인 Grain Metadata ID(자유 문자열이 아니다) |
| `join_ids` | `array[string]` | 필수(빈 배열 허용) | 사용한 승인 Join Metadata ID 목록 |
| `order_by` | `array[object]` | 필수(최소 1개) | 정렬 기준 목록. [`order_by[]` 구조](#order_by-구조) 참고 |
| `limit` | `integer` | 필수, 1 이상 | 강제 TOP N 값 |
| `depth` | `integer` | 필수 | 현재 Workflow Depth |

### `filters[]` 구조

| 필드 | 타입 | 필수 여부 | 의미 |
|---|---|---|---|
| `filter_id` | `string` | 필수, trim 후 비어 있지 않음 | Metadata Context에 존재하는 승인 Filter Metadata ID. Metric ID를 여기 넣지 않는다 |
| `parameters` | `object` | 필수(값이 없으면 `{}`) | 이 Filter에 필요한 Parameter. 각 값은 [RuntimeIntent Contract의 `explicit_parameters`](runtime-intent.md#explicit_parameters-허용-값-범위)와 동일하게 JSON 원시 타입(`string`, `number`, `boolean`)만 허용하며 중첩 `object`, `array`와 `null`은 허용하지 않는다 |

`filter_id`와 `parameters` 외의 추가 필드를 포함하면 Contract를 만족하지 않는 것으로 처리한다. 같은 `filter_id`를 여러 항목에서 중복 사용하면 Contract를 만족하지 않는 것으로 처리한다.

### `order_by[]` 구조

| 필드 | 타입 | 필수 여부 | 의미 |
|---|---|---|---|
| `field_id` | `string` | 필수, trim 후 비어 있지 않음 | 정렬 대상 필드 ID. 같은 QueryPlan의 `dimension_ids` 또는 `metric_ids`에 포함된 ID만 허용한다 |
| `direction` | `string` (Enum) | 필수 | `asc` 또는 `desc` |

`field_id`와 `direction` 외의 추가 필드를 포함하면 Contract를 만족하지 않는 것으로 처리한다. 같은 `field_id`를 여러 항목에서 중복 정렬하면 Contract를 만족하지 않는 것으로 처리한다. `filters[]`와 `order_by[]` 배열의 순서는 SQL 생성과 결과 순서에 의미가 있으므로 그대로 보존해야 한다.

## FEAT-0004 전용 규칙

* `depth`는 반드시 `1`이어야 한다. `1`이 아닌 값은 Backend가 거부한다.
* `grain_id`는 `product`만 허용한다. 다른 값은 Backend가 거부한다.
* `order_by`는 최소 1개 이상의 정렬 기준을 포함해야 하며, 비어 있으면 Backend가 거부한다. 대표 재고 질문의 첫 번째 정렬 기준은 `product_id` `asc`여야 한다. 결정적인 정렬이 필요한 이유는 [FEAT-0004 Spec](../features/0004-natural-language-query-walking-skeleton/spec.md)을 따른다.
* 결과에 노출할 제품 식별·표시 필드(예: 제품 ID, 제품명)는 `dimension_ids`에 명시적으로 포함해야 하며, SQL Generator가 Metadata Context를 참고해 QueryPlan에 없는 Dimension을 임의로 결과에 추가하지 않아야 한다.
* `limit`은 [`execute_readonly_query` Contract](execute-readonly-query.md)가 정의하는 `maximum_returned_rows` 허용 범위 안이어야 하며, 실행 시 실제로 사용하는 `maximum_returned_rows` 이하여야 한다.

## 공통 불변조건

* 모든 ID 문자열(`entity_id`, `dimension_ids[]`, `metric_ids[]`, `filters[].filter_id`, `time_policy_id`, `grain_id`, `join_ids[]`, `order_by[].field_id`)과 `purpose`는 trim 후 비어 있을 수 없다.
* QueryPlan은 이 문서가 정의한 최상위 필드만 가지며, 정의되지 않은 추가 필드를 포함하면 Contract를 만족하지 않는 것으로 처리한다.
* `dimension_ids`, `metric_ids`, `join_ids`는 각각 배열 안에서 중복 ID를 허용하지 않는다.
* `metric_ids`는 최소 1개 이상이어야 한다.
* `order_by[].field_id`는 같은 QueryPlan의 `dimension_ids` 또는 `metric_ids`에 포함된 ID만 참조할 수 있다.
* QueryPlan이 참조하는 모든 ID(`entity_id`, `dimension_ids[]`, `metric_ids[]`, `filters[].filter_id`, `time_policy_id`, `grain_id`, `join_ids[]`, `order_by[].field_id`)는 Metadata Context에 존재하는 승인 Metadata만 참조해야 하며, Context에 없는 ID를 참조하면 Backend는 이 QueryPlan을 거부하고 SQL을 생성하지 않는다.

## MVP Level 1 Validator 범위

* 참조한 Metadata ID(`entity_id`, `dimension_ids`, `metric_ids`, `filters[].filter_id`, `time_policy_id`, `grain_id`, `join_ids`, `order_by[].field_id`)가 Metadata Context에 존재하는지 여부
* 사용자와 역할의 ACL(Week 1은 고정 Demo Scope로 대체)
* 허용된 Entity, Dimension, Metric, Filter, Grain ID
* 관리자 승인 Join ID
* `filters[].parameters` 형식과 허용 범위(JSON 원시 타입만 허용, 중첩 금지)
* Workflow Depth(`depth=1`)와 결과 Limit
* `order_by`가 최소 1개 이상이고 각 `field_id`가 `dimension_ids`·`metric_ids`에 존재하는지 여부
* 정의되지 않은 추가 필드, 중복 ID(`dimension_ids`·`metric_ids`·`join_ids`·`filters[].filter_id`·`order_by[].field_id`) 포함 여부

Metric ID에 승인된 공식과 Grain 정보가 포함될 수는 있지만 MVP Validator가 공식의 수학적 타당성이나 Metric 간 집계 호환성을 해석한다는 의미는 아니다. Formula, Aggregation, Grain과 Semantic Validation은 Post-MVP Level 2 범위다.

## 대표 재고 질문 QueryPlan 예시

질문: "현재 재고가 안전재고보다 부족한 제품을 보여줘"

```json
{
  "purpose": "안전재고보다 현재 재고가 부족한 제품을 조회한다",
  "entity_id": "product",
  "dimension_ids": ["product_id", "product_name"],
  "metric_ids": ["current_inventory", "safety_stock_level"],
  "filters": [
    {
      "filter_id": "below_safety_stock",
      "parameters": {}
    }
  ],
  "time_policy_id": null,
  "grain_id": "product",
  "join_ids": ["product_to_product_inventory"],
  "order_by": [
    {
      "field_id": "product_id",
      "direction": "asc"
    }
  ],
  "limit": 100,
  "depth": 1
}
```

## SQL Guardrail과의 경계

SQL Guardrail은 QueryPlan이 아니라 생성된 SQL 자체를 정적으로 검사한다.

* SQL AST 파싱과 단일 Statement 강제
* SELECT-only와 금지 구문 차단
* Table·Column Allowlist
* 승인된 Join 확인
* TOP N 강제와 최대값 확인
* QueryPlan과 SQL의 테이블·컬럼·Join·Limit 구조적 일치 확인

SQL Formula·Aggregation·Grain이 Plan의 업무 의미와 동일한지 판정하는 의미적 일치 검증은 Post-MVP Level 2다. Week 1(FEAT-0004)은 QueryPlan 존재·ACL·ID·Parameter·Depth·Limit 검증과 SQL의 최소 실행 제한만 적용하며, 전체 SQL AST Guardrail과 구조적 Plan-SQL Match는 FEAT-0006부터 적용한다. MVP에서는 대표 지표의 의미와 계산 결과를 Golden Query 회귀 테스트로 보완한다.
