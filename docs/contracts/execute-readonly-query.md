# 읽기 전용 쿼리 Tool 계약 (`execute_readonly_query` Contract)

> 이 문서는 FastAPI의 MCP Client Manager가 검증 완료 SQL을 MCP Server에 전달하고 조회 결과를 돌려받는 입출력 계약을 정의한다.

## 상태

초안 (Proposed). 필드의 최종 Pydantic Schema는 Week 2 구현과 함께 확정한다.

## 이 문서를 읽는 이유

* Tool에 전달할 수 있는 값을 확인한다.
* 성공 결과와 데이터 직렬화 형식을 확인한다.
* 행 제한과 오류가 어떻게 표현되는지 확인한다.

## 범위

이 문서는 `execute_readonly_query`의 입력, 성공 결과와 오류 전달 규칙을 정의한다. 로컬 `stdio`와 프로세스 Lifecycle을 선택한 이유는 [ADR 0007](../adr/0007-local-stdio-mcp-db-boundary.md)에서 설명한다.

## 관련 문서

* [MCP 컴포넌트 경계](../architecture/component-boundaries.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [QueryPlan Contract](query-plan.md)

## 입력 Contract

Tool은 자연어 질문, RuntimeIntent, ACL 정보 또는 LLM Tool Call 원문을 입력으로 받지 않는다. 최소 논리 입력은 다음과 같다.

| 필드 | 의미 |
|---|---|
| `sql` | Backend SQL Guardrail과 구조적 Plan-SQL Match를 통과한 단일 SELECT SQL |
| `parameters` | SQL 문자열과 분리된 바인딩 파라미터 |
| `correlation_id` | 질문, 실행과 Audit을 연결하는 식별자 |
| `query_timeout_seconds` | MCP Server가 DB 명령 실행에 적용할 DB Query Timeout |
| `maximum_returned_rows` | Tool이 반환할 수 있는 최대 행 수 |

MCP Server는 호출자가 전달한 값을 신뢰하지 않고 SELECT-only, 단일 Statement와 최소 실행 안전성을 재검증한다.

## 성공 반환 Contract

성공한 Tool 호출은 다음 구조의 JSON 직렬화 가능한 결과를 반환한다.

```json
{
  "correlation_id": "01JEXAMPLE",
  "columns": ["ProductID", "Name", "ListPrice"],
  "rows": [
    [707, "Sport-100 Helmet, Red", "34.9900"]
  ],
  "row_count": 1,
  "truncated": false,
  "execution_ms": 18
}
```

| 필드 | 의미 |
|---|---|
| `correlation_id` | 요청에서 전달받은 추적 식별자 |
| `columns` | 조회 결과 컬럼명 순서 |
| `rows` | `columns`와 같은 순서를 사용하는 행 배열 |
| `row_count` | 실제 반환된 행 수 |
| `truncated` | Maximum Returned Rows 때문에 결과가 잘렸는지 여부 |
| `execution_ms` | MCP Server에서 측정한 DB 실행 시간 |

## 직렬화 규칙

* SQL `NULL`은 JSON `null`로 반환한다.
* Decimal은 정밀도 손실을 피하기 위해 문자열로 반환한다.
* 날짜와 시간은 ISO 8601 문자열로 반환한다.
* 성공 결과에는 자연어 설명이나 LLM 해석을 포함하지 않는다.

## 오류 규칙

실행 실패는 성공 결과에 포함하지 않고 MCP 오류로 반환한다. MCP Client Manager는 MCP Call Timeout, 연결 종료와 Tool 오류를 Backend의 명시적 오류 타입으로 변환하며 대상 DB 직접 실행으로 우회하지 않는다.
