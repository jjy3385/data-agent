# 전체 아키텍처 개요 (Architecture Overview)

> 이 문서는 B2B SQL Data Agent의 전체 구성요소와 가장 중요한 데이터 흐름을 한눈에 설명한다. 상세 구현에 들어가기 전에 시스템의 방향을 다시 확인할 때 읽는다.

## 핵심 구조

FastAPI 백엔드는 Workflow Orchestrator 역할을 담당한다. LLM의 제안을 그대로 실행하지 않고 ACL, 승인 Metadata, QueryPlan과 SQL Guardrail을 검증한 뒤 MCP Client Manager를 통해서만 대상 DB에 접근한다.

```text
[Jinja2 Demo Web UI / HTTP API]
        ▲
        ▼
┌────────────────────────────────────────────────┐
│ Workflow Orchestrator (FastAPI, single worker) │
│ · Correlation ID · Role/ACL · RuntimeIntent    │
│ · QueryPlan · SQL Guardrail · XAI/Audit        │
└───────────────┬───────────────┬─────────────────┘
                │              └────────────▶ LLM Provider
                ├─────────────────────▶ Admin DB
                │                       Metadata · Policy · Audit
                │ 검증 완료 SQL + 실행 제한
                ▼
       ┌──────────────────────────────┐
       │ MCP Client Manager           │
       │ · Official MCP SDK Client    │
       │ · Long-lived Client Session  │
       │ · Serialization · Call Timeout│
       └───────────────┬──────────────┘
                │ local stdio
                ▼
       ┌──────────────────────────────┐
       │ MCP Server (subprocess)      │
       │ · inspect_schema             │
       │ · execute_readonly_query     │
       │ · Read-Only Query Executor   │
       │ · DB Timeout · Maximum Rows  │
       └───────────────┬──────────────┘
                ▼
       [Read-Only MSSQL / AdventureWorks]
```

## 반드시 유지할 방향

* LLM은 Raw Enterprise Database를 직접 해석하거나 조회하지 않는다.
* ACL과 승인 Metadata를 통과한 정보만 Query Planning에 사용한다.
* SQL Guardrail을 통과한 SQL만 MCP Client Manager에 전달한다.
* 대상 DB 접근은 승인된 MCP Tool을 통해서만 수행한다.
* MCP 장애 시 FastAPI의 직접 DB 실행 경로로 우회하지 않는다.
* MVP에서는 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 Bounded Result를 Result Handle 없이 LLM에 직접 전달한다.
* Jinja2 데모 웹 UI는 FastAPI를 통해서만 Metadata와 승인된 Sample 데이터를 조회하며 임의 SQL 입력을 제공하지 않는다.
* Slack 입력·응답 Adapter는 Post-MVP 범위다.

## 관련 문서

* [컴포넌트 경계](component-boundaries.md)
* [질문 처리 시퀀스](query-execution-sequence.md)
* [MVP 범위](../mvp/scope.md)
* [MCP 실행 경계 ADR](../adr/0007-local-stdio-mcp-db-boundary.md)
