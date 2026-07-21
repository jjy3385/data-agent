# 4주 MVP 로드맵 (MVP Roadmap)

> 이 문서는 현재 개발 위치와 다음 구현 순서를 관리한다. 작업을 시작하거나 우선순위를 바꿀 때 이 체크리스트를 먼저 갱신한다.

## 현재 방향

MVP는 Business Metadata와 Security Foundation을 먼저 만들고 RuntimeIntent, QueryPlan, SQL Guardrail, MCP 실행, Depth 2, XAI와 Slack을 순서대로 연결한다.

## Week 1: Business Metadata & Security Foundation

* [ ] FastAPI 프로젝트 기본 구조
* [ ] Admin DB(SQLite) DDL (`users`, `audit_logs`, `table_policies`, `error_reports`)
* [ ] MCP Server 전용 AdventureWorks2022 Read-Only 연결
* [ ] 대상 MSSQL 카탈로그·Physical FK 수집용 MCP Schema Inspection Tool
* [ ] Provider 교체 가능한 LLM Client와 환경설정 검증
* [ ] 대표 질문용 Entity, Dimension, Metric과 Time Policy
* [ ] Metadata Alias·Keyword Catalog와 RuntimeIntent Contract
* [ ] 테이블·컬럼 Allowlist와 승인 Join Metadata
* [ ] Depth 1·2 예상 QueryPlan, Golden Query와 예상 결과
* [ ] `supply_risk_analyst`, `inventory_viewer` 역할과 ACL 정책
* [ ] 역할별 Metadata Retrieval과 Context Builder

## Week 2: RuntimeIntent, Depth 1 & Guardrail

* [ ] LLM API Client
* [ ] Pydantic 기반 RuntimeIntent 구조화 출력과 검증
* [ ] RuntimeIntent 기반 Metadata Retrieval과 ACL 교집합
* [ ] Retrieval 결과 기반 Metadata Context 생성
* [ ] LLM Depth 1 QueryPlan과 Backend Level 1 Validator
* [ ] 검증된 Plan 기반 LLM MSSQL 생성
* [ ] SQL Guardrail의 AST, SELECT-only와 금지 구문 검사
* [ ] Table·Column Allowlist, 승인 Join, TOP N과 구조적 Plan-SQL Match
* [ ] FastAPI Lifespan 기반 로컬 `stdio` MCP Server와 장기 유지 Session
* [ ] 공식 MCP SDK 기반 MCP Client Manager와 필수 Tool 입력 Contract 검증
* [ ] `execute_readonly_query` MCP Tool과 Read-Only Query Executor
* [ ] MCP Client Manager의 MCP Call Timeout과 오류 매핑
* [ ] Executor의 SELECT-only·단일 Statement 재검증, DB Timeout과 Maximum Rows
* [ ] 공유 MCP Client Session 요청 직렬화
* [ ] Depth 1 예상 Plan과 Golden Query 회귀 테스트

## Week 3: Depth 2, XAI & Slack

* [ ] TOP N·허용 컬럼·Maximum Rows가 적용된 Bounded Result 직접 전달
* [ ] LLM Next Action과 Backend 대상 선택
* [ ] Depth 2 QueryPlan 검증, LLM SQL 생성과 Guardrail
* [ ] 최대 2-Depth, 실행당 1-Retry와 Self-Healing
* [ ] Backend 근거 Payload 기반 XAI 응답
* [ ] Slack Bot 연동
* [ ] Correlation ID 기반 Intent·Plan·SQL·Bounded Result Audit Log

## Week 4: Failure Paths & E2E

* [ ] 역할별 허용·거부 E2E 테스트
* [ ] LLM Provider 설정과 Client 교체 가능성 검증 테스트
* [ ] 위험 SQL 차단 E2E 테스트
* [ ] 잘못된 QueryPlan과 Plan-SQL 불일치 차단 테스트
* [ ] Bounded Result의 행·컬럼 제한과 Result Handle 없는 Direct 전달 테스트
* [ ] 허용 범위 밖 Depth 2 대상 차단 테스트
* [ ] SQL 오류와 1-Retry E2E 테스트
* [ ] MCP 시작·초기화·Tool Contract 실패와 실행 중 연결 종료 테스트
* [ ] FastAPI 종료 시 MCP Session과 하위 프로세스 정상 종료 테스트
* [ ] Slack 오류 신고와 원본 실행 연결
* [ ] 대표 시나리오 전체 E2E 회귀 테스트
* [ ] Docker Compose 실행 검증

## Post-MVP

Formula·Aggregation·Grain Semantic Validator, 범용 Schema Collection, Metadata Import, 완전한 Metadata CRUD API와 Admin UI는 대표 시나리오 완료 후 진행한다.

## 관련 문서

* [MVP 범위](scope.md)
* [MVP 완료 기준](acceptance-criteria.md)
* [개발 프로토콜](../development-protocol.md)
