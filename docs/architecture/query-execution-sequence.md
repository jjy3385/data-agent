# 질문 처리 시퀀스 (Query Execution Sequence)

> 이 문서는 Slack 자연어 질문이 ACL 검증, QueryPlan, SQL Guardrail, MCP 실행과 XAI 응답을 거치는 전체 순서를 설명한다. 기능 구현이나 E2E 테스트에서 단계가 빠졌는지 확인할 때 사용한다.

## 관련 문서

* [전체 아키텍처](overview.md)
* [컴포넌트 경계](component-boundaries.md)
* [Contract 목록](../contracts/)
* [MVP 완료 기준](../mvp/acceptance-criteria.md)

## 전체 처리 흐름

1. **Slack 질문 수신 및 Correlation ID 생성:** 하나의 질문, Depth 1·2 실행, 최종 응답과 오류 신고를 연결할 추적 ID를 발급한다.

2. **사용자·역할·ACL 확인:** Slack ID를 Admin DB 사용자와 매핑하고 허용된 Entity, Dimension, Metric, 테이블과 컬럼 정책을 확인한다.

3. **Runtime Intent Resolution:** LLM이 자연어에서 요청 유형, 대상 Entity, 업무 개념, 원하는 결과 형태와 모호한 조건을 `RuntimeIntent`로 구조화한다.

4. **RuntimeIntent 검증:** Backend가 Pydantic Schema, 필수 필드, Enum, Parameter 형식과 명확화 여부를 검사한다. 유효하지 않으면 이후 단계로 진행하지 않는다.

5. **ACL-scoped Metadata Retrieval:** RuntimeIntent를 검색 입력으로 사용하고 ACL이 허용한 승인 Metadata Catalog에서 Entity, Dimension, Metric, Time Policy와 Join을 조회한다.

6. **Metadata Context 생성:** Retrieval 결과만 LLM Context에 포함한다. 필요한 Metadata가 없거나 질문이 모호하면 명확화를 요청하거나 Fail Closed 처리한다.

7. **Depth 1 QueryPlan 생성:** LLM이 승인 Metadata ID를 조합해 Dimension, Metric, Filter, Time Policy, Grouping, Ordering과 TOP N을 포함한 Plan을 만든다.

8. **Level 1 Plan Validation:** Backend가 Metadata 존재 여부, ACL, 허용 ID, 승인 Join, Parameter 범위, Depth와 Limit을 검증한다.

9. **MSSQL 생성:** LLM이 검증된 QueryPlan과 제한된 MSSQL Context를 사용해 SQL을 생성한다.

10. **SQL Guardrail:** Backend가 SQL AST, SELECT-only, 단일 Statement, Table·Column Allowlist, 승인 Join, TOP N, 금지 구문과 구조적 Plan-SQL Match를 정적으로 검사한다.

11. **MCP Read-Only Query 실행:** MCP Client Manager가 검증 완료 SQL과 바인딩 파라미터, Correlation ID, DB Query Timeout과 Maximum Returned Rows를 `execute_readonly_query`에 전달한다. MCP Server는 최소 실행 안전성을 재검증한 뒤 Read-Only 계정으로 조회한다.

12. **제한된 Result Context 생성:** Backend가 Raw Result에 TOP N, 허용 컬럼과 데이터 최소화 정책을 적용해 Result Summary와 LLM Projection을 만든다.

13. **Private LLM Next Action:** Private LLM이 최소 Projection을 바탕으로 `STOP`, `DRILL_DOWN`, `ASK_CLARIFICATION` 중 하나를 반환한다.

14. **Backend 대상 선택:** Backend가 행동을 검증하고 Depth 1 Raw Result 안에서만 Depth 2의 실제 대상과 PK를 제한된 수로 선택한다.

15. **Depth 2 Plan·SQL·실행:** Depth 1과 같은 Plan Validation, SQL Guardrail과 MCP 실행 경계를 적용한다.

16. **근거 기반 XAI와 최종 응답:** Backend가 실제 Plan, Metadata, SQL, 데이터 기준일, 계산식과 한계로 XAI Payload를 구성하고 LLM은 그 범위 안에서 설명을 작성한다.

17. **Audit 및 오류 신고:** Intent, Metadata Context, Plan, SQL, Guardrail, Projection, Next Action, 실행 시간, 조회 행 수와 응답을 Correlation ID로 연결한다.

## Self-Healing 경계

SQL 실행 오류에 대한 Self-Healing은 각 실행에서 최대 1회만 허용한다. 재생성된 SQL도 동일한 QueryPlan과 ACL 범위를 벗어날 수 없고 모든 Guardrail을 다시 통과해야 한다.
