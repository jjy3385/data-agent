# 런타임 의도 계약 (RuntimeIntent Contract)

> 이 문서는 사용자의 자연어 질문을 Metadata 검색과 Query Planning에 사용할 구조화된 입력으로 변환하는 `RuntimeIntent` 계약을 정의한다.

## 상태

승인됨 (Accepted). [FEAT-0004 자연어 질문 처리 최소 동작 흐름](../features/0004-natural-language-query-walking-skeleton/spec.md)의 구현 기준으로 사용한다.

## 이 문서를 읽는 이유

* Intent Resolver가 어떤 필드를 반환하는지 확인한다.
* 각 필드의 타입, 필수 여부와 허용 값을 확인한다.
* RuntimeIntent가 결정할 수 있는 것과 결정하면 안 되는 것을 구분한다.
* 명확화가 필요한 질문을 SQL 생성 전에 차단하는 조건을 확인한다.

## 범위

이 문서는 FEAT-0004 구현에 필요한 최소 수준까지 RuntimeIntent의 필드, 타입, 허용 값과 불변조건을 확정한다. 기존에 설명 수준으로만 존재하던 의미를 불필요하게 확장하지 않는다. Metadata 검색 결과, QueryPlan과 SQL 구조는 각각 관련 Contract에서 정의한다.

## 관련 문서

* [QueryPlan Contract](query-plan.md)
* [자연어 질문 API Contract](natural-language-query.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP 범위](../mvp/scope.md)
* [FEAT-0004 자연어 질문 처리 최소 동작 흐름 Spec](../features/0004-natural-language-query-walking-skeleton/spec.md)

## 정의

RuntimeIntent는 미리 등록된 업무 시나리오 식별자가 아니라 현재 자연어 요청을 구조화한 런타임 산출물이다. Intent Resolver는 아래 JSON 구조를 만족하는 RuntimeIntent를 반환해야 한다. 정의되지 않은 추가 필드를 포함하면 Contract를 만족하지 않는 것으로 처리한다.

## JSON 구조

```json
{
  "request_type": "lookup",
  "subject": "product",
  "requested_concepts": ["inventory", "safety_stock"],
  "requested_output": "list",
  "explicit_parameters": {},
  "requires_clarification": false,
  "clarification_reason": null
}
```

| 필드 | 타입 | 필수 여부 | 의미 |
|---|---|---|---|
| `request_type` | `string` (Enum) | 필수 | 요청 형태. [허용 Enum](#request_type-허용-enum) 중 하나만 허용 |
| `subject` | `string` | 필수(`requires_clarification=true`이면 빈 문자열 허용) | 질문의 중심 Entity 후보(예: 제품, 공급업체, 지역). 검색 입력일 뿐 승인 Metadata ID가 아니다 |
| `requested_concepts` | `array[string]` | 필수 | 사용자 표현에서 추출한 Metadata 검색어 목록. [비어 있지 않은 배열 조건](#requested_concepts-조건) 참고 |
| `requested_output` | `string` (Enum) | 필수 | 원하는 결과 형태. [허용 Enum](#requested_output-허용-enum) 중 하나만 허용 |
| `explicit_parameters` | `object` | 필수(값이 없으면 `{}`) | 사용자가 직접 말한 기간, 개수, 임계값 등 원시 값. [허용 값 범위](#explicit_parameters-허용-값-범위) 참고 |
| `requires_clarification` | `boolean` | 필수 | 안전한 Metadata 검색 또는 Plan 생성 전에 명확화가 필요한지 여부 |
| `clarification_reason` | `string \| null` | 필수 | 명확화가 필요한 이유. [조건 관계](#requires_clarification과-clarification_reason의-조건-관계) 참고 |

### `request_type` 허용 Enum

| 값 | 의미 |
|---|---|
| `lookup` | 조건에 맞는 대상을 찾아 보여주는 단순 조회 |
| `aggregation` | 합계·평균 등 집계 결과 요청 |
| `comparison` | 둘 이상의 대상이나 시점을 비교하는 요청 |
| `ranking` | 순서를 매겨 상위·하위를 요청 |
| `complex_investigation` | 여러 개념을 조합한 복합 조사 요청 |

정의되지 않은 값은 Contract 위반으로 처리한다.

### `requested_output` 허용 Enum

| 값 | 의미 |
|---|---|
| `list` | 대상 목록 |
| `summary` | 요약된 값 |
| `ranking` | 순위가 매겨진 목록 |
| `investigation` | 근거를 포함한 조사 결과 |

정의되지 않은 값은 Contract 위반으로 처리한다.

### `requested_concepts` 조건

* `requires_clarification`이 `false`이면 `requested_concepts`는 최소 1개 이상의 원소를 가진 배열이어야 한다. 빈 배열이면 Contract 위반으로 처리한다.
* `requires_clarification`이 `true`이면 아직 개념을 특정하지 못했을 수 있으므로 빈 배열(`[]`)을 허용한다.

### `explicit_parameters` 허용 값 범위

* `key`는 짧은 소문자 식별자 문자열이다(예: `"limit"`, `"period_days"`, `"threshold"`).
* `value`는 JSON 원시 타입(`string`, `number`, `boolean`)만 허용하며 중첩된 객체나 배열은 허용하지 않는다.
* 이 필드는 사용자가 명시한 원시 값만 담으며, 기간 정책·공식·집계 Grain·Join처럼 이후 단계에서 승인 Metadata로부터만 결정해야 하는 값을 채워 넣지 않는다.
* 값이 승인된 범위 안에 있는지 여부는 이 Contract가 아니라 이후 QueryPlan 검증 단계에서 확인한다.

### `requires_clarification`과 `clarification_reason`의 조건 관계

* `requires_clarification = false` ⇔ `clarification_reason = null`.
* `requires_clarification = true` ⇔ `clarification_reason`은 비어 있지 않은 문자열이어야 한다.
* 두 조건 중 하나라도 어긋나면(예: `requires_clarification=true`인데 `clarification_reason`이 `null`이거나 빈 문자열) Contract 위반으로 처리한다.

## 대표 재고 질문 예시

질문: "현재 재고가 안전재고보다 부족한 제품을 보여줘"

```json
{
  "request_type": "lookup",
  "subject": "product",
  "requested_concepts": ["inventory", "safety_stock"],
  "requested_output": "list",
  "explicit_parameters": {},
  "requires_clarification": false,
  "clarification_reason": null
}
```

## 불변조건

* `requested_concepts`와 `subject`는 승인된 Metadata ID가 아니라 검색 입력이다.
* Intent Resolution은 "최근=90일", "재고 부족=안전재고 미만" 같은 업무 의미를 결정하지 않는다.
* 기간 정책, 공식, 집계 Grain과 Join은 이후 검색된 승인 Metadata에서만 가져온다.
* RuntimeIntent는 위에서 정의한 7개 필드만 가지며, 정의되지 않은 추가 필드를 포함하면 Contract를 만족하지 않는 것으로 처리한다.
* `request_type`과 `requested_output`은 각각 정의된 Enum 값 중 하나여야 한다.
* Backend는 위 필드 타입, Enum 값과 `requested_concepts`·`requires_clarification`·`clarification_reason` 조건을 모두 검증해야 한다.
* Contract를 만족하지 않거나(타입 불일치, Enum 밖의 값, 조건 위반, 추가 필드 포함) `requires_clarification`이 `true`이면 Backend는 Metadata Retrieval, QueryPlan 생성 또는 SQL 생성으로 진행하지 않아야 한다.
