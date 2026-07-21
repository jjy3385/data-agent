# MVP 완료 기준 (Acceptance Criteria)

> 이 문서는 MVP를 완료했다고 판단하기 위한 Golden Query와 E2E 검증 조건을 정의한다. 기능 구현 여부가 아니라 실제 안전성과 결과를 이 목록으로 판정한다.

## Golden Query

Golden Query는 사람이 업무 정의와 결과를 검증한 기준 SQL이다. 런타임 답변을 하드코딩하기 위한 것이 아니라 LLM, Prompt, Metadata, QueryPlan 또는 Workflow 변경 후에도 대표 질문의 의미와 결과가 유지되는지 확인하는 회귀 테스트 기준이다.

## 완료 체크리스트

* [ ] Depth 1과 Depth 2에 대해 검토·승인된 Golden Query와 예상 결과가 있다.
* [ ] 자연스러운 대표 질문에서 Schema를 준수하는 RuntimeIntent가 생성된다.
* [ ] RuntimeIntent와 ACL로 검색된 승인 Metadata만 Query Planner Context에 포함된다.
* [ ] Metadata가 없거나 Intent가 모호하면 명확화를 요청하거나 Fail Closed 처리한다.
* [ ] QueryPlan은 승인된 Entity, Dimension, Metric, Time Policy와 Join ID만 참조한다.
* [ ] Depth 1과 Depth 2 Plan이 Metadata, ACL, 허용 ID, 승인 Join, Parameter, Depth와 Limit 검증을 통과한다.
* [ ] Agent가 생성한 SQL의 핵심 결과 집합과 계산값이 Golden Query와 일치한다.
* [ ] `supply_risk_analyst`는 대표 질문의 전체 2-Depth 결과를 조회할 수 있다.
* [ ] `inventory_viewer`의 대표 질문은 판매·구매 Metadata를 LLM에 노출하지 않고 SQL 생성 전에 거부된다.
* [ ] 권한 위반 요청은 SQL 실행 전에 차단된다.
* [ ] 모든 SQL은 AST, SELECT-only, Allowlist, 승인 Join과 TOP N Guardrail을 통과한다.
* [ ] MVP Plan-SQL Match는 테이블·컬럼·Join·Limit의 구조적 일치를 검사한다.
* [ ] 대상 DB 접근은 승인된 로컬 `stdio` MCP Tool을 통해서만 수행된다.
* [ ] 업무 조회 Tool은 검증된 SQL만 입력으로 받고 FastAPI에는 직접 실행 대체 경로가 없다.
* [ ] MCP 초기화, Tool Discovery 또는 필수 Contract 검증 실패 시 애플리케이션이 Fail Closed한다.
* [ ] MCP Client Manager는 MCP Call Timeout을 적용한다.
* [ ] Read-Only Query Executor는 DB Query Timeout과 Maximum Returned Rows를 강제한다.
* [ ] 공유 MCP Client Session을 사용하는 대상 DB 실행 요청은 Backend에서 직렬화된다.
* [ ] Agent Workflow는 최대 Depth 2, SQL Self-Healing은 실행당 1회를 초과하지 않는다.
* [ ] `LLM_DEPLOYMENT_MODE=private`와 승인된 Private Endpoint만 사용한다.
* [ ] Raw Result 전체 대신 TOP N과 허용 컬럼을 적용한 최소 Projection만 LLM에 전달한다.
* [ ] LLM Next Action은 허용 행동으로 제한하고 Depth 2 대상은 Backend가 Depth 1 결과 안에서 선택한다.
* [ ] Slack 응답에 기준일, 계산식, 판단 근거와 데이터 한계가 포함된다.
* [ ] Intent, Context, Plan, SQL, Projection과 실행 단계가 하나의 Correlation ID로 연결된다.
* [ ] 오류 신고가 원래 실행 이력과 연결된다.

## 관련 문서

* [MVP 범위](scope.md)
* [MVP 로드맵](roadmap.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [Contract 목록](../contracts/)
