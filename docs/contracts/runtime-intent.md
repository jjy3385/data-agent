# 런타임 의도 계약 (RuntimeIntent Contract)

> 이 문서는 사용자의 자연어 질문을 Metadata 검색과 Query Planning에 사용할 구조화된 입력으로 변환하는 `RuntimeIntent` 계약을 정의한다.

## 이 문서를 읽는 이유

* Intent Resolver가 어떤 필드를 반환하는지 확인한다.
* RuntimeIntent가 결정할 수 있는 것과 결정하면 안 되는 것을 구분한다.
* 명확화가 필요한 질문을 SQL 생성 전에 차단한다.

## 범위

이 문서는 RuntimeIntent의 최소 필드, 의미와 불변조건을 정의한다. Metadata 검색 결과, QueryPlan과 SQL 구조는 각각 관련 Contract에서 정의한다.

## 관련 문서

* [QueryPlan Contract](query-plan.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP 범위](../mvp/scope.md)

## 정의

RuntimeIntent는 미리 등록된 업무 시나리오 식별자가 아니라 현재 자연어 요청을 구조화한 런타임 산출물이다. Intent Resolver는 Pydantic Schema를 만족하는 동일한 Contract를 반환해야 한다.

```json
{
  "request_type": "ranking",
  "subject": "product",
  "requested_concepts": [
    "sales",
    "inventory"
  ],
  "requested_output": "list",
  "explicit_parameters": {},
  "requires_clarification": false,
  "clarification_reason": null
}
```

| 필드 | 의미 |
|---|---|
| `request_type` | 조회, 집계, 비교, 순위, 복합 조사 등 허용된 요청 형태 Enum |
| `subject` | 제품, 공급업체, 지역 등 질문의 중심 Entity 후보 |
| `requested_concepts` | 판매, 재고, 공급 상황 등 사용자 표현에서 추출한 Metadata 검색어 |
| `requested_output` | 목록, 요약, 순위, 근거 조사 등 원하는 결과 형태 Enum |
| `explicit_parameters` | 사용자가 직접 말한 기간, 개수, 임계값 등의 구조화된 값 |
| `requires_clarification` | 안전한 Metadata 검색 또는 Plan 생성 전에 명확화가 필요한지 여부 |
| `clarification_reason` | 명확화가 필요한 이유이며 필요하지 않으면 `null` |

## 불변조건

* `requested_concepts`와 `subject`는 승인된 Metadata ID가 아니라 검색 입력이다.
* Intent Resolution은 “최근=90일”, “재고 부족=안전재고 미만” 같은 업무 의미를 결정하지 않는다.
* 기간 정책, 공식, 집계 Grain과 Join은 이후 검색된 승인 Metadata에서만 가져온다.
* Contract가 유효하지 않거나 `requires_clarification`이 참이면 Metadata Retrieval이나 SQL 생성으로 진행하지 않는다.
