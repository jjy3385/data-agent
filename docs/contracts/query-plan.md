# 쿼리 계획 계약 (QueryPlan Contract)

> 이 문서는 자연어와 SQL 사이의 검증 가능한 중간 표현인 QueryPlan의 구성요소와 MVP 검증 범위를 정의한다.

## 이 문서를 읽는 이유

* LLM Query Planner가 무엇을 출력해야 하는지 확인한다.
* Backend Validator가 어떤 항목을 차단하는지 확인한다.
* MVP Level 1 검증과 Post-MVP 의미 검증의 경계를 구분한다.

## 범위

이 문서는 QueryPlan의 논리 구성과 검증 범위를 정의한다. SQL 실행 Tool의 형식은 [`execute_readonly_query` Contract](execute-readonly-query.md)에서 정의한다.

## 관련 문서

* [RuntimeIntent Contract](runtime-intent.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP 완료 기준](../mvp/acceptance-criteria.md)

## 구성요소

LLM은 QueryPlan에서 관리자 승인 Metadata ID만 참조해야 하며 Backend 검증을 통과한 Plan만 SQL로 변환할 수 있다.

| 구성요소 | 내용 |
|---|---|
| Purpose | 질문을 어떻게 해석했는지에 대한 실행 목적 |
| Entity / Dimension | 제품, 위치, 공급업체 등 조회와 그룹화 기준 |
| Metric | 승인된 업무 지표 ID |
| Filter / Parameter | 비교 조건과 허용 범위 안의 사용자 입력 |
| Time Policy | 승인된 기준일과 기본·명시 기간 |
| Grain / Grouping | 결과 한 행의 의미와 집계 수준 |
| Join IDs | 관리자 승인 Join Metadata 참조 |
| Order / Limit | 정렬 기준과 강제 TOP N |
| Depth / Purpose | 현재 Workflow Depth와 단계 목적 |

## MVP Level 1 Validator 범위

* 참조한 Metadata ID의 존재 여부
* 사용자와 역할의 ACL
* 허용된 Entity, Dimension, Metric ID
* 관리자 승인 Join ID
* Parameter 형식과 허용 범위
* Workflow Depth와 결과 Limit

Metric ID에 승인된 공식과 Grain 정보가 포함될 수는 있지만 MVP Validator가 공식의 수학적 타당성이나 Metric 간 집계 호환성을 해석한다는 의미는 아니다. Formula, Aggregation, Grain과 Semantic Validation은 Post-MVP Level 2 범위다.

## SQL Guardrail과의 경계

SQL Guardrail은 QueryPlan이 아니라 생성된 SQL 자체를 정적으로 검사한다.

* SQL AST 파싱과 단일 Statement 강제
* SELECT-only와 금지 구문 차단
* Table·Column Allowlist
* 승인된 Join 확인
* TOP N 강제와 최대값 확인
* QueryPlan과 SQL의 테이블·컬럼·Join·Limit 구조적 일치 확인

SQL Formula·Aggregation·Grain이 Plan의 업무 의미와 동일한지 판정하는 의미적 일치 검증은 Post-MVP Level 2다. MVP에서는 대표 지표의 의미와 계산 결과를 Golden Query 회귀 테스트로 보완한다.
