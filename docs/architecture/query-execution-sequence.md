# 질문 처리 시퀀스 (Query Execution Sequence)

> 이 문서는 HTTP 자연어 질문이 ACL 검증, QueryPlan, SQL Guardrail, MCP 실행과 XAI 응답을 거치는 최종 MVP 순서를 설명한다. 기능 구현이나 E2E 테스트에서 단계가 빠졌는지 확인할 때 사용한다.

## 관련 문서

* [전체 아키텍처](overview.md)
* [컴포넌트 경계](component-boundaries.md)
* [Contract 목록](../contracts/)
* [MVP 완료 기준](../mvp/acceptance-criteria.md)

## 전체 처리 흐름

1. **HTTP 질문 수신 및 Correlation ID 생성:** 하나의 질문, Depth 1·2 실행과 최종 응답을 연결할 추적 ID를 발급한다. Swagger와 Jinja2 데모 웹 UI는 같은 Backend 흐름을 사용한다.

2. **사용자·역할·ACL 확인:** 요청 사용자 식별자를 Admin DB 사용자와 매핑하고 허용된 Entity, Dimension, Metric, 테이블과 컬럼 정책을 확인한다.

3. **Runtime Intent Resolution:** LLM이 자연어에서 요청 유형, 대상 Entity, 업무 개념, 원하는 결과 형태와 모호한 조건을 `RuntimeIntent`로 구조화한다.

4. **RuntimeIntent 검증:** Backend가 Pydantic Schema, 필수 필드, Enum, Parameter 형식과 명확화 여부를 검사한다. 유효하지 않으면 이후 단계로 진행하지 않는다.

5. **ACL-scoped Metadata Retrieval:** RuntimeIntent를 검색 입력으로 사용하고 ACL이 허용한 승인 Metadata Catalog에서 Entity, Dimension, Metric, Time Policy와 Join을 조회한다.

6. **Metadata Context 생성:** Retrieval 결과만 LLM Context에 포함한다. 필요한 Metadata가 없거나 질문이 모호하면 명확화를 요청하거나 Fail Closed 처리한다.

7. **Depth 1 QueryPlan 생성:** LLM이 승인 Metadata ID를 조합해 Dimension, Metric, Filter, Time Policy, Grouping, Ordering과 TOP N을 포함한 Plan을 만든다.

8. **Level 1 Plan Validation:** Backend가 Metadata 존재 여부, ACL, 허용 ID, 승인 Join, Parameter 범위, Depth와 Limit을 검증한다.

9. **MSSQL 생성:** LLM이 검증된 QueryPlan과 제한된 MSSQL Context를 사용해 SQL을 생성한다.

10. **SQL Guardrail:** Backend가 SQL AST, SELECT-only, 단일 Statement, Table·Column Allowlist, 승인 Join, TOP N, 금지 구문과 구조적 Plan-SQL Match를 정적으로 검사한다.

11. **MCP Read-Only Query 실행:** MCP Client Manager가 검증 완료 SQL과 바인딩 파라미터, Correlation ID, DB Query Timeout과 Maximum Returned Rows를 `execute_readonly_query`에 전달한다. MCP Server는 최소 실행 안전성을 재검증한 뒤 Read-Only 계정으로 조회한다.

12. **Bounded Result 확인 및 Direct 전달:** Backend가 MCP 실행 결과에 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용됐는지 확인한다. Depth 1에서 종료하면 API 결과로 반환하고, 다음 행동 판단이 필요하면 Result Handle 없이 LLM에 직접 전달한다.

13. **LLM Next Action:** LLM이 Bounded Result를 바탕으로 `STOP`, `DRILL_DOWN`, `ASK_CLARIFICATION` 중 하나를 반환한다.

14. **Backend 대상 선택:** Backend가 행동을 검증하고 Depth 1 Bounded Result 안에서만 Depth 2의 실제 대상과 PK를 제한된 수로 선택한다.

15. **Depth 2 Plan·SQL·실행:** Depth 1과 같은 Plan Validation, SQL Guardrail과 MCP 실행 경계를 적용한다.

16. **근거 기반 XAI와 최종 응답:** Backend가 실제 Plan, Metadata, SQL, 데이터 기준일, 계산식과 한계로 XAI Payload를 구성하고 LLM은 그 범위 안에서 설명을 작성한다.

17. **Audit:** Intent, Metadata Context, Plan, SQL, Guardrail, Bounded Result, Next Action, 실행 시간, 조회 행 수와 응답을 Correlation ID로 연결한다.

## 단계별 구현 범위

이 순서는 최종 MVP Architecture이며 한 번에 모두 구현하지 않는다.

* Week 1은 대표 재고 질문에 대해 1~12단계를 연결하고 Depth 1 결과를 반환한다. 2, 4~10단계는 Demo 사용자와 고정 Demo Scope에 대한 최소 Contract·정책·실행 제한으로 시작한다.
* Week 2는 Admin DB 사용자·정책 기반 2, 4~10단계와 17단계의 안전·실패 경계를 완성하고 AWS에 배포한다.
* Week 3은 13~16단계를 추가해 최대 Depth 2와 XAI를 완성한다.

SQL Self-Healing과 Slack 입력·응답 Adapter는 Post-MVP 범위다.
