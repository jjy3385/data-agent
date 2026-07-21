# 컴포넌트 책임과 경계 (Component Boundaries)

> 이 문서는 FastAPI Workflow Orchestrator, MCP Client Manager, MCP Server, Admin DB와 LLM Provider의 책임을 구분한다. 어느 계층에 코드를 작성해야 할지 헷갈릴 때 기준으로 사용한다.

## 이 문서가 정의하는 범위

* 주요 컴포넌트의 책임과 금지사항
* MCP 프로세스와 Session Lifecycle
* SQL Guardrail, MCP Call Timeout과 DB Query Timeout의 경계

정확한 Tool 필드는 [`execute_readonly_query` Contract](../contracts/execute-readonly-query.md)를, MCP 구조 선택 이유는 [ADR 0007](../adr/0007-local-stdio-mcp-db-boundary.md)을 따른다.

## Workflow Orchestrator

FastAPI 내부의 `agent_service.py`가 Workflow Orchestrator의 논리적 책임을 구현한다.

* Correlation ID와 요청 처리 순서 관리
* Slack 사용자, 역할과 ACL 평가
* RuntimeIntent와 QueryPlan Contract 검증
* 승인 Metadata Retrieval과 제한된 Context 생성
* SQL Guardrail과 구조적 Plan-SQL Match
* 최대 Depth 2와 실행당 Self-Healing 1회 통제
* Result Context, XAI Payload와 Audit 구성

Workflow Orchestrator는 대상 DB 드라이버를 사용하거나 SQL을 직접 실행하지 않는다.

## MCP Client Manager

FastAPI 내부 구성요소이며 공식 MCP SDK Client를 사용한다.

* FastAPI Lifespan 동안 MCP Server 하위 프로세스와 장기 유지 Client Session 관리
* MCP 초기화, Tool Discovery와 필수 Tool 입력 Contract 검증
* 검증 완료 SQL과 제한된 실행 인자를 `execute_readonly_query` 호출로 변환
* 공유 Session의 대상 DB 실행 요청 직렬화
* MCP Call Timeout 적용
* 연결 종료, Tool 오류와 Timeout을 Backend 오류로 변환
* FastAPI 종료 시 Session과 하위 프로세스 정리

MVP는 FastAPI 워커 하나와 MCP Server 프로세스 하나만 지원한다. 병렬 실행, Session Pool과 Process Pool은 Post-MVP 범위다.

## MCP Server와 Read-Only Query Executor

MCP Server는 대상 DB 연결과 실제 실행을 소유한다.

* Read-Only 대상 DB 계정과 드라이버 Lifecycle
* SELECT-only와 단일 Statement 재검증
* DB Query Timeout과 Maximum Returned Rows 강제
* JSON 직렬화 가능한 구조화 결과 반환
* `stdout`은 MCP Protocol 전용으로 사용
* 일반 로그와 진단 정보는 `stderr` 또는 별도 Log Sink로 출력

MCP Server는 QueryPlan에서 SQL을 생성하지 않고 FastAPI가 검증한 SQL만 실행한다. 자연어 질문, RuntimeIntent, ACL 정보나 LLM Tool Call 원문을 입력으로 받지 않는다.

## Timeout 책임

| 계층 | 책임 |
|---|---|
| SQL Guardrail | SQL 구조와 정책의 정적 검증. 실행 시간을 제어하지 않음 |
| MCP Client Manager | Backend가 MCP 응답을 기다리는 MCP Call Timeout |
| Read-Only Query Executor | DB Driver에 적용하는 DB Query Timeout |

MCP Call Timeout이 발생했다고 DB 작업이 즉시 중단됐다고 가정하지 않는다. DB 실행 제한은 MCP Server에서 별도로 강제한다.

## Admin DB와 대상 DB

* Admin DB는 사용자, ACL, 승인 Metadata, Audit과 오류 신고를 저장한다.
* 대상 DB는 AdventureWorks2022 업무 데이터이며 MCP Server를 통해서만 접근한다.
* Admin DB 접근은 MCP 대상 DB 실행 경계의 적용 대상이 아니다.

## LLM Provider

* RuntimeIntent, QueryPlan, SQL, Next Action과 최종 설명 생성에 사용한다.
* ACL로 제한된 Metadata Context만 받는다.
* MVP에서는 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 Bounded Result를 직접 받는다.
* Post-MVP Private 모드는 MVP의 Direct 경로를 재사용한다.
* Post-MVP External 모드는 Result Handle과 최소 Summary 또는 Projection을 받는다.
* 어떤 모드에서도 SQL 실행 권한이나 대상 선택 최종 권한을 갖지 않는다.

상세 결과 전달 정책은 [ADR 0006](../adr/0006-result-handle.md)과 [Result Context Contract](../contracts/result-context.md)를 따른다.
