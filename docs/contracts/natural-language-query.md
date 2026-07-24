# 자연어 질문 API 계약 (Natural Language Query Contract)

> 이 문서는 사용자가 자연어 질문을 HTTP로 보내고 Bounded Result 또는 구조화된 명확화·거부·실패 응답을 받는 논리적 입출력 계약을 정의한다.

## 상태

승인됨 (Accepted). [FEAT-0004 자연어 질문 처리 최소 동작 흐름](../features/0004-natural-language-query-walking-skeleton/spec.md)의 구현 기준으로 사용한다.

## 이 문서를 읽는 이유

* 자연어 질문 API에 전달할 수 있는 값을 확인한다.
* 성공, 명확화, 거부와 실패 응답의 논리적 구조를 확인한다.
* HTTP 응답에 노출하면 안 되는 정보를 확인한다.
* Correlation ID가 모든 응답에서 어떻게 관찰되는지 확인한다.

## 범위

이 문서는 정확한 HTTP 경로, 메서드와 HTTP 상태 코드를 고정하지 않는다. 이는 Plan 단계의 기술 결정이다. 이 문서는 요청과 응답의 논리적 필드, 타입과 상태 구분만 정의한다.

## 관련 문서

* [RuntimeIntent Contract](runtime-intent.md)
* [QueryPlan Contract](query-plan.md)
* [`execute_readonly_query` Contract](execute-readonly-query.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [FEAT-0004 자연어 질문 처리 최소 동작 흐름 Spec](../features/0004-natural-language-query-walking-skeleton/spec.md)

## 요청 Contract

| 필드 | 타입 | 필수 여부 | 의미 |
|---|---|---|---|
| `question` | `string` | 필수, 비어 있지 않은 문자열 | 사용자의 자연어 질문 원문 |

요청 Contract는 `question` 필드만 정의한다. Client는 SQL, RuntimeIntent, QueryPlan 또는 대상 DB 연결 설정(`TARGET_DB_*` 등)에 해당하는 값을 포함해 정의되지 않은 추가 필드를 요청에 보낼 수 없다.

```json
{
  "question": "현재 재고가 안전재고보다 부족한 제품을 보여줘"
}
```

### 정의되지 않은 추가 필드 처리

요청에 `question` 외의 필드가 하나라도 포함되어 있으면 Backend는 이를 무시하고 계속 처리하지 않고 반드시 `status: "rejected"`, `code: "invalid_request"`로 거부해야 한다. 이 규칙은 예외 없이 적용하며, 추가 필드에 담긴 값(SQL, RuntimeIntent, QueryPlan, 대상 DB 설정 등)을 RuntimeIntent 생성, Metadata Retrieval, QueryPlan 생성 또는 SQL 생성의 입력으로 사용해서는 안 된다.

## 응답 Contract

모든 응답은 `correlation_id`와 `status`를 포함한다. `status`는 다음 네 값 중 하나다.

| `status` | 의미 |
|---|---|
| `completed` | 질문이 실제 MCP 조회까지 성공적으로 처리되어 Bounded Result를 반환한다 |
| `clarification_required` | SQL을 생성·실행하지 않고 사용자에게 추가 정보를 요청한다 |
| `rejected` | 사용자 입력이나 해석 결과가 현재 지원 범위·정책상 안전하게 처리할 수 없어 SQL을 생성·실행하지 않는다 |
| `failed` | LLM 호출 또는 MCP 실행 등 시스템·외부 의존성 문제로 요청을 완료하지 못했다 |

`correlation_id`는 `completed`, `clarification_required`, `rejected`, `failed` 네 응답 모두에 포함되어 사용자가 관찰할 수 있어야 한다.

### 성공 응답 (`status: "completed"`)

| 필드 | 타입 | 의미 |
|---|---|---|
| `correlation_id` | `string` | 이 요청의 추적 식별자 |
| `status` | `string` | `"completed"` 고정값 |
| `bounded_result` | `object` | 아래 표의 필드로 구성된 Bounded Result |

`bounded_result`는 [`execute_readonly_query` Contract](execute-readonly-query.md)의 성공 결과를 기반으로 하되, 이 API의 논리적 응답 경계로 재정의한다.

| `bounded_result` 필드 | 타입 | 의미 |
|---|---|---|
| `columns` | `array[string]` | 조회 결과 컬럼명 순서 |
| `rows` | `array[array]` | `columns`와 같은 순서를 사용하는 행 배열 |
| `row_count` | `integer` | `rows`에 실제로 담겨 반환된 행 수 |
| `truncated` | `boolean` | Maximum Returned Rows 때문에 `rows`에 담기지 않은 추가 행이 있으면 `true` |
| `execution_ms` | `integer` | 대상 DB 실행 시간 |

```json
{
  "correlation_id": "01JEXAMPLE",
  "status": "completed",
  "bounded_result": {
    "columns": ["ProductID", "Name", "CurrentInventory", "SafetyStockLevel"],
    "rows": [[707, "Sport-100 Helmet, Red", "3", "4"]],
    "row_count": 1,
    "truncated": false,
    "execution_ms": 42
  }
}
```

### 비성공 응답 (`status: "clarification_required" | "rejected" | "failed"`)

| 필드 | 타입 | 의미 |
|---|---|---|
| `correlation_id` | `string` | 이 요청의 추적 식별자 |
| `status` | `string` | `"clarification_required"`, `"rejected"` 또는 `"failed"` |
| `code` | `string` (Enum) | 안전한 원인 분류 코드. [허용 코드](#code-허용-값) 참고 |
| `message` | `string` | 사용자에게 그대로 보여줄 수 있는 안전한 설명 |

```json
{
  "correlation_id": "01JEXAMPLE",
  "status": "rejected",
  "code": "metadata_not_found",
  "message": "이 질문에 필요한 정보를 현재 지원 범위에서 찾을 수 없습니다."
}
```

### `code` 허용 값

| `status` | `code` | 의미 |
|---|---|---|
| `clarification_required` | `clarification_required` | 질문이 모호하거나 정보가 부족해 실행 전에 추가 확인이 필요하다 |
| `rejected` | `invalid_request` | 요청 자체가 Contract를 만족하지 않는다(예: `question`이 비어 있거나 허용되지 않은 필드를 포함) |
| `rejected` | `intent_contract_violation` | 생성된 RuntimeIntent가 RuntimeIntent Contract를 만족하지 않는다 |
| `rejected` | `metadata_not_found` | 질문에 필요한 Business Metadata가 없거나 고정 Demo Scope를 벗어난다 |
| `rejected` | `query_plan_invalid` | QueryPlan이 참조한 Metadata나 고정 Demo Scope 허용 범위 검증을 통과하지 못했다 |
| `rejected` | `sql_rejected` | 생성된 SQL이 최소 실행 제한(SELECT-only, 허용 Table·Column, TOP N 등)을 통과하지 못했다 |
| `failed` | `llm_unavailable` | 설정된 LLM Provider가 없거나 유효하지 않거나 호출에 실패했다 |
| `failed` | `mcp_execution_failed` | 정상적으로 시작된 이후 요청을 처리하는 도중 MCP Call Timeout, 연결 종료, Tool 오류 또는 DB Query Timeout으로 실행을 완료하지 못했다. FastAPI Startup 단계의 MCP 초기화·Tool Discovery·Tool Contract 검증·`inspect_schema`·Physical Metadata Catalog 구성 실패는 이 `code`로 표현하지 않는다. 그 경우 ASGI Startup 자체가 완료되지 않아 이 API가 요청을 받지 않으며, 이는 FEAT-0003이 정의한 기존 Fail Closed 경계를 그대로 재사용한다 |
| `failed` | `internal_error` | 위에서 정의한 LLM·MCP·검증 오류 범주로 분류할 수 없는 예상하지 못한 내부 실패. 원본 Exception, Stack Trace 또는 내부 구현 정보를 노출하지 않는 고정된 안전 메시지를 사용한다 |

이 표는 이 Contract가 정의하는 공개 `code` Enum 전체다. 공개 `code` 값을 추가하거나 변경하려면 이 Contract 문서를 함께 수정하고 재검토해야 하며, Plan 단계에서 이 Contract를 수정하지 않고 임의로 공개 `code`를 확장할 수 없다.

## 노출 금지 정보

`message`를 포함한 어떤 HTTP 응답 필드에도 다음을 포함하지 않아야 한다.

* 원본 Prompt 전문
* LLM이 반환한 원문 오류 메시지
* 대상 DB Driver의 원문 오류 메시지
* 대상 DB 자격 증명이나 연결 문자열
* 내부 Stack Trace

## 불변조건

* 모든 응답은 `correlation_id`를 포함해야 하며, 이 값은 [질문 처리 시퀀스](../architecture/query-execution-sequence.md)가 정의하는 것처럼 RuntimeIntent, Metadata Context, QueryPlan, SQL과 MCP 실행 전체 단계와 동일해야 한다.
* `status`가 `clarification_required` 또는 `rejected`이면 SQL을 생성·실행하지 않았어야 하며, `bounded_result`를 포함하지 않아야 한다.
* `status`가 `failed`이면 `bounded_result`를 포함하지 않아야 한다. `llm_unavailable`은 SQL 생성·실행 전에 발생하지만, `mcp_execution_failed`는 SQL 실행을 요청했거나 대상 DB 실행이 시작된 뒤 발생할 수 있고 `internal_error`는 발생 지점에 따라 SQL 실행 여부가 달라질 수 있다.
* `status`가 `completed`이면 `bounded_result`는 실제 MCP `execute_readonly_query` 실행 결과를 기반으로 해야 하며 LLM이 생성한 값으로 대체하지 않아야 한다.
* Client가 요청에 `question` 외의 정의되지 않은 필드를 포함하면 Backend는 이를 무시하고 계속 처리하지 않고 반드시 `rejected`/`invalid_request`로 거부해야 하며, 그 값을 RuntimeIntent·QueryPlan·SQL 생성에 사용해서는 안 된다.
* `internal_error`를 포함해 이 문서의 [`code` 허용 값](#code-허용-값) 표에 없는 `code`를 응답에 사용해서는 안 되며, 새로운 공개 `code`가 필요하면 이 Contract를 먼저 수정해야 한다.
