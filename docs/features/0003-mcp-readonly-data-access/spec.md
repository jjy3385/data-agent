# MCP Read-Only Data Access Spec

* Feature ID: `FEAT-0003`
* Status: `Approved`
* Development Track: `Standard`
* Track 선택 근거: 대상 DB 접근 경계, Read-Only 권한, 외부 프로세스(MCP Server) Lifecycle과 Fail Closed 동작을 포함하므로 Standard Track을 적용한다.
* Roadmap: [Week 1 - FEAT-0003 MCP Read-Only Data Access](../../mvp/roadmap.md#week-1-local-depth-1-demo)

## 목적

FastAPI가 대상 AdventureWorks2022 데이터베이스에 직접 연결하지 않고, FastAPI가 관리하는 로컬 `stdio` MCP Server와 공식 MCP SDK Client를 통해서만 대상 DB에 접근하는 실행 경계를 만든다. 이 경계 위에서 두 가지를 제공한다: 읽기 전용 Schema Inspection(`inspect_schema`)으로 AdventureWorks2022의 사용자 정의 Physical Schema 정보를 수집하고 Backend가 이를 애플리케이션이 실제로 조회·사용할 수 있는 Physical Metadata Catalog로 구성하는 것, 그리고 Backend가 검증한 단일 SELECT만 안전하게 실행하는 Read-Only Query 실행(`execute_readonly_query`)이다. 이렇게 구성된 Physical Metadata Catalog는 FEAT-0004 자연어 질문 처리와 FEAT-0005 Jinja2 데모 웹 UI가 사용할 수 있는 기반이 된다. 이 Feature 자체는 자연어 질문을 처리하지 않으며, 후속 Feature(FEAT-0004, FEAT-0006)가 이 실행 경계 위에 자연어 질문 처리와 ACL을 쌓을 수 있는 기반을 제공하는 것이 목표다.

## 범위

포함:

* AdventureWorks2022 전용 Read-Only 연결
* MCP Server와 FastAPI MCP Client Lifecycle
* `inspect_schema` Tool
* `execute_readonly_query` Tool
* Schema Inspection 결과로 구성하는 Physical Metadata Catalog
* 대상 DB 연결 설정과 연결 준비 실패 처리
* 기본 연결·Timeout·행 제한·종료·실패 동작
* Tool Contract와 실행 경계 검증

제외:

* LLM 호출
* 자연어 질문 API
* RuntimeIntent 생성
* QueryPlan 생성
* LLM 기반 MSSQL 생성
* 사용자·역할·Table Policy 기반 ACL 적용
* 전체 SQL AST Guardrail과 Plan-SQL Match
* Business Metadata 작성 또는 자동 추론
* Jinja2 데모 웹 UI
* AWS 배포와 Docker 기반 애플리케이션 배포 구조
* Slack 연동
* SQL Self-Healing
* 다중 MCP Server, Session Pool, Process Pool과 병렬 DB 실행
* 원격 MCP Transport와 서비스 간 인증
* 범용 다중 데이터베이스 Schema 수집
* 임의 사용자가 호출할 수 있는 SQL Console 또는 공개 MCP Tool

FEAT-0004는 이 Feature가 제공하는 실행 경계를 사용해 자연어 질문에서 Depth 1 결과까지 연결한다. FEAT-0006은 실제 사용자 ACL과 전체 Validation·Guardrail을 적용한다.

## 사용자 또는 시스템 시나리오

### 시나리오 1: 애플리케이션이 MCP 실행 경계를 준비한다

* Given: AdventureWorks2022에 접근 가능한 Read-Only 자격 증명과 MCP Server 실행 환경이 준비되어 있다.
* When: FastAPI 애플리케이션이 시작된다.
* Then: FastAPI Lifespan 동안 유지되는 로컬 `stdio` MCP Server 프로세스 하나와 장기 유지 MCP Client Session 하나가 생성되고, MCP 초기화·Tool Discovery·필수 Tool Contract 검증을 통과한 뒤 애플리케이션이 정상 시작한다.

### 시나리오 2: Physical Schema를 검사하고 Physical Metadata Catalog를 구성한다

* Given: MCP 실행 경계가 준비되어 있다.
* When: Backend가 `inspect_schema`를 호출한다.
* Then: `Sales`, `Production`, `Purchasing`을 포함한 AdventureWorks2022의 사용자 정의 Schema와 Table을 대상으로 Schema·Table·Column·데이터 타입·Nullability·Primary Key·Physical Foreign Key와 DB에 등록된 Table·Column 설명이 반환되고, Backend는 이 결과로 애플리케이션이 조회·사용할 수 있는 Physical Metadata Catalog를 실제로 구성한다. 시스템 Schema와 시스템 객체는 결과에 포함되지 않는다.

### 시나리오 3: 검증된 SQL을 실행한다

* Given: Backend가 하나의 SELECT SQL과 바인딩 Parameter, Correlation ID, DB Query Timeout과 Maximum Returned Rows를 검증했다.
* When: Backend가 `execute_readonly_query`를 호출한다.
* Then: MCP Server가 Read-Only 계정으로 실행해 JSON으로 직렬화 가능한 제한된 결과(컬럼, 행, 실제 반환된 행 수, 잘림 여부)를 반환한다.

### 시나리오 4: 여러 요청이 공유 Session을 순차적으로 사용한다

* Given: 여러 대상 DB 실행 요청이 비슷한 시점에 발생한다.
* When: 요청들이 같은 MCP Client Session을 통해 처리된다.
* Then: Backend가 요청을 직렬화해 MCP Server가 한 번에 하나의 요청만 처리한다.

### 시나리오 5: 애플리케이션이 정상 종료된다

* Given: FastAPI 애플리케이션이 실행 중이며 MCP Server 프로세스와 Session이 유지되고 있다.
* When: 애플리케이션 종료가 요청된다.
* Then: MCP Client Session과 MCP Server 하위 프로세스가 정리된 뒤 애플리케이션이 종료된다.

### 실패 시나리오 1: MCP 실행 경계를 준비할 수 없다

* Given: MCP Server를 시작할 수 없거나 초기화, Tool Discovery 또는 필수 Tool Contract 검증이 실패한다.
* When: 애플리케이션 시작을 시도한다.
* Then: 애플리케이션이 정상 상태로 시작하지 않는다.

### 실패 시나리오 2: 허용되지 않는 SQL을 실행하려 한다

* Given: `execute_readonly_query`에 다중 Statement 또는 쓰기 SQL이 전달된다.
* When: MCP Server가 실행 직전 안전성을 재검증한다.
* Then: Backend의 사전 검증 여부와 무관하게 실행이 거부된다.

### 실패 시나리오 3: 실행이 DB Query Timeout을 초과한다

* Given: 대상 DB 조회가 지정된 DB Query Timeout 안에 끝나지 않는다.
* When: MCP Server가 DB Query Timeout을 적용한다.
* Then: 구조화된 Timeout 오류가 MCP Client Manager를 거쳐 Backend에 전달된다.

### 실패 시나리오 4: 실행 중 MCP 연결이 끊어진다

* Given: `execute_readonly_query` 실행 중 MCP Session 또는 하위 프로세스 연결이 끊어진다.
* When: MCP Client Manager가 이 상태를 감지한다.
* Then: 구조화된 오류로 Backend에 전달되며, FastAPI는 대상 DB로 직접 우회하는 실행 경로를 사용하지 않는다.

### 실패 시나리오 5: 허용되지 않는 입력으로 Tool을 호출하려 한다

* Given: 자연어 질문, RuntimeIntent, ACL 원문 또는 LLM Tool Call 원문을 `execute_readonly_query`에 직접 전달하려 한다.
* When: 호출이 시도된다.
* Then: Tool 입력 Contract가 이러한 필드를 받아들이지 않아 호출이 성립하지 않는다.

### 실패 시나리오 6: 대상 DB 설정 또는 연결 준비에 실패한다

* Given: 필수 `TARGET_DB_*` 설정이 누락되었거나 비어 있거나 유효하지 않거나, 설정은 유효하지만 대상 DB에 연결할 수 없다.
* When: MCP Server가 시작 시 대상 DB 연결을 준비한다.
* Then: MCP 실행 경계가 준비된 것으로 처리되지 않고 애플리케이션이 정상 상태로 시작하지 않는다.

## 기능 요구사항

* `FR-001`: 시스템은 FastAPI가 AdventureWorks2022에 직접 연결하지 않고, 대상 DB 접근이 승인된 MCP Tool을 통해서만 이뤄지도록 해야 한다.
* `FR-002`: 시스템은 FastAPI Lifespan 동안 하나의 로컬 `stdio` MCP Server 프로세스와 하나의 장기 유지 MCP Client Session을 생성하고 모든 요청에서 재사용해야 하며, 요청마다 새 프로세스나 Session을 만들지 않아야 한다.
* `FR-003`: 시스템은 공식 MCP SDK Client를 사용해야 하며 MCP Wire Protocol을 직접 구현하지 않아야 한다.
* `FR-004`: 시스템은 애플리케이션 시작 시 MCP Server 시작, 초기화, Tool Discovery와 필수 Tool 입력 Contract와의 호환성을 검증해야 하며, 실패하면 애플리케이션이 정상 시작하지 않아야 한다.
* `FR-005`: 시스템은 `inspect_schema` Tool을 제공해 AdventureWorks2022의 사용자 정의 Schema(`Sales`, `Production`, `Purchasing` 포함)와 Table을 읽기 전용으로 검사할 수 있어야 하며, 시스템 Schema와 시스템 객체는 검사 대상에서 제외해야 한다([`inspect_schema` Contract](../../contracts/inspect-schema.md) 참고).
* `FR-006`: `inspect_schema`의 결과는 최소한 Schema, Table, Column, 데이터 타입, Nullability, Primary Key와 Physical Foreign Key를 식별할 수 있는 정보와 SQL Server의 `MS_Description`에 등록된 Table·Column 설명을 포함해야 한다. 설명이 등록되지 않은 경우 `null`을 반환해야 하며, 설명 부재로 Schema Inspection을 실패시키지 않아야 한다.
* `FR-007`: Backend는 `inspect_schema` 결과를 사용해 애플리케이션이 조회·사용할 수 있는 Physical Metadata Catalog를 실제로 구성해야 하며, 이 Catalog는 후속 자연어 질문 처리(FEAT-0004)와 Jinja2 데모 웹 UI(FEAT-0005)가 사용할 수 있는 형태여야 한다.
* `FR-008`: `inspect_schema`는 DB에 등록된 `MS_Description` 원문을 Physical Metadata로 수집할 수 있지만 이를 자동 번역·요약·보강하거나, 업무 용어, Metric, 계산식, Grain, Time Policy나 Join 의미 같은 Business Metadata로 자동 추론·승격하지 않아야 한다.
* `FR-009`: 시스템은 `execute_readonly_query` Tool을 제공해 Backend가 검증을 완료한 단일 MSSQL SELECT Statement만 실행할 수 있어야 한다.
* `FR-010`: `execute_readonly_query`는 자연어 질문, RuntimeIntent, ACL 원문 또는 LLM Tool Call 원문을 입력으로 받지 않아야 하며, [`execute_readonly_query` Contract](../../contracts/execute-readonly-query.md)가 정의하는 입력만 받아야 한다.
* `FR-011`: MCP Server는 호출자가 전달한 SQL이 Backend에서 이미 검증됐더라도 실행 직전에 SELECT-only와 단일 Statement 여부, 그 밖의 최소 실행 안전성을 다시 검사해야 한다.
* `FR-012`: MCP Server는 DB Query Timeout과 Maximum Returned Rows를 강제해야 하며, Timeout 초과는 구조화된 오류로, 행 수 초과는 결과가 잘렸음을 표시하는 방식으로 처리해야 한다.
* `FR-013`: 시스템은 공유 MCP Client Session에 대한 대상 DB 실행 요청을 Backend에서 직렬화해야 한다.
* `FR-014`: MCP Server는 `stdout`을 MCP Protocol 전용으로 사용해야 하며, 일반 로그와 진단 정보는 `stderr` 또는 별도 Log Sink를 사용해야 한다.
* `FR-015`: 실행 중 연결 종료, Timeout 또는 Tool 오류가 발생하면 MCP Client Manager는 이를 구조화된 실패로 Backend에 전달해야 하며, FastAPI는 대상 DB 직접 실행으로 우회하지 않아야 한다.
* `FR-016`: 시스템은 FastAPI 종료 시 MCP Client Session과 MCP Server 하위 프로세스를 정리해야 한다.
* `FR-017`: MCP Server는 `mcp_tutorial`이 이미 사용한 `TARGET_DB_HOST`, `TARGET_DB_PORT`, `TARGET_DB_NAME`, `TARGET_DB_USER`, `TARGET_DB_PASSWORD`, `TARGET_DB_DRIVER`, `TARGET_DB_ENCRYPT`, `TARGET_DB_TRUST_SERVER_CERTIFICATE` 환경변수 이름을 그대로 사용해 대상 DB 연결 설정을 소유해야 하며, FastAPI 서비스 코드는 대상 MSSQL Driver나 이 설정에 대한 직접 접근을 사용하지 않아야 한다.
* `FR-018`: 필수 대상 DB 설정이 누락되었거나 비어 있거나 유효하지 않으면 시스템은 이를 안전하게 거부해야 하며, 대상 DB 연결 준비에 실패하면 MCP 실행 경계가 준비된 것으로 처리하지 않아야 한다.

## 비기능 요구사항

* `NFR-001`: 대상 DB 계정은 실제 쓰기 권한이 없는 Read-Only 계정이어야 하며, 이 보장은 SQL Guardrail 같은 애플리케이션 계층 검증만으로 대체되지 않아야 한다.
* `NFR-002`: MCP Call Timeout(MCP Client Manager 책임)과 DB Query Timeout(MCP Server 책임)은 서로 다른 계층에서 독립적으로 관리해야 하며, 한쪽의 Timeout이 다른 쪽의 실행 중단을 의미한다고 가정하지 않아야 한다.
* `NFR-003`: MVP는 FastAPI 워커 하나와 MCP Server 프로세스 하나만 지원해야 하며, 다중 MCP Server, Session Pool, Process Pool 또는 병렬 대상 DB 실행을 지원하지 않아야 한다.
* `NFR-004`: MVP MCP Transport는 로컬 `stdio`만 지원해야 하며, 원격 MCP Transport나 서비스 간 인증을 요구하지 않아야 한다.
* `NFR-005`: 이 Feature는 자연어 질문 처리, RuntimeIntent, QueryPlan, LLM 호출, 사용자 ACL 평가 또는 SQL AST 수준 Guardrail을 구현하지 않아야 한다.
* `NFR-006`: MCP Tool은 임의 사용자가 자유롭게 호출할 수 있는 공개 SQL Console 형태로 노출되지 않아야 하며, FastAPI가 관리하는 내부 실행 구성요소로만 존재해야 한다.
* `NFR-007`: 대상 DB 자격 증명의 실제 값은 로그, 문서 또는 Tool 결과에 노출되지 않아야 한다.

## Acceptance Criteria

* [ ] FastAPI는 대상 DB 드라이버를 직접 사용하지 않고, 대상 DB 접근은 MCP Server를 통해서만 이뤄진다.
* [ ] FastAPI Lifespan 동안 MCP Server 프로세스 하나와 MCP Client Session 하나가 유지되고, 여러 요청이 같은 Session을 재사용한다.
* [ ] MCP Server 시작, 초기화, Tool Discovery 또는 필수 Tool Contract 검증이 실패하면 애플리케이션이 정상 서비스 상태로 시작하지 않는다.
* [ ] `inspect_schema`는 `Sales`, `Production`, `Purchasing`을 포함한 사용자 정의 Schema와 Table을 대상으로 하고 시스템 Schema와 시스템 객체를 제외한다.
* [ ] `inspect_schema` 결과로 Schema, Table, Column, 데이터 타입, Nullability, Primary Key, Physical Foreign Key와 DB에 등록된 Table·Column `MS_Description`을 식별할 수 있고, 설명이 없는 경우 `null`로 처리된다.
* [ ] Backend가 `inspect_schema` 결과로 Physical Metadata Catalog를 실제로 구성하고, FEAT-0004와 FEAT-0005가 이를 조회·사용할 수 있다.
* [ ] `inspect_schema`는 `MS_Description` 원문을 자동 번역·요약·보강하거나 업무 용어, Metric, 계산식, Grain, Time Policy나 Join 의미 같은 Business Metadata로 자동 추론·승격하지 않는다.
* [ ] `execute_readonly_query`는 자연어 질문, RuntimeIntent, ACL 원문 또는 LLM Tool Call 원문을 입력으로 받지 않고, 검증된 SQL·Parameter·Correlation ID·Timeout·행 제한만 입력으로 받는다.
* [ ] `execute_readonly_query`로 쓰기 SQL이나 다중 Statement를 실행할 수 없다.
* [ ] `execute_readonly_query`는 DB Query Timeout과 Maximum Returned Rows를 강제하고, 결과가 잘리면 이를 표시한다.
* [ ] 대상 DB 계정은 Read-Only이며 실제로 쓰기 작업이 거부된다.
* [ ] 공유 MCP Session에 대한 실행 요청은 Backend에서 직렬화되어 처리된다.
* [ ] MCP Server의 `stdout`은 Protocol 전용으로 유지되고 일반 로그가 섞이지 않는다.
* [ ] 실행 중 연결 종료, Timeout 또는 Tool 오류는 구조화된 오류로 Backend에 전달되고, FastAPI는 대상 DB로 직접 우회하지 않는다.
* [ ] FastAPI 종료 시 MCP Client Session과 MCP Server 하위 프로세스가 정리된다.
* [ ] 자연어 질문 처리, RuntimeIntent, QueryPlan, ACL 평가와 전체 SQL AST Guardrail은 이 Feature의 결과물에 포함되지 않는다.
* [ ] MCP Tool은 임의 사용자가 직접 호출할 수 있는 공개 경로 없이 FastAPI가 관리하는 내부 구성요소로만 존재한다.
* [ ] MCP Server는 `mcp_tutorial`이 사용한 `TARGET_DB_*` 환경변수 이름으로 대상 DB 연결 설정을 소유하고, FastAPI 서비스 코드는 대상 MSSQL Driver나 이 설정을 직접 사용하지 않는다.
* [ ] 필수 대상 DB 설정이 없거나 비어 있거나 유효하지 않으면 거부되고, 대상 DB 연결 준비가 실패하면 MCP 실행 경계가 준비된 것으로 처리되지 않는다.
* [ ] 대상 DB 자격 증명의 실제 값이 로그, 문서 또는 Tool 결과에 노출되지 않는다.

## 가정과 제약

* 대상 DB 실행 경계는 [ADR 0001 Read-Only Target Database Access](../../adr/0001-readonly-db.md)와 [ADR 0007 Local stdio MCP DB Boundary](../../adr/0007-local-stdio-mcp-db-boundary.md)가 정의한 경계를 그대로 따른다.
* AdventureWorks2022는 로컬 Docker SQL Server에 복원된 단일 DB를 기준으로 검증한다([MVP 범위](../../mvp/scope.md)). AWS/Docker 기반 애플리케이션 배포 구조 자체는 이 Feature의 범위가 아니다.
* `mcp_tutorial/`은 대상 DB Read-Only 연결과 MCP SDK 사용 가능성을 사전에 검증한 참고 자료이며, 이 Feature의 구현 대상이 아니다. 이 Feature는 `mcp_tutorial/`의 코드나 실행 환경을 재사용하지 않지만, 이미 검증된 `TARGET_DB_*` 환경변수 이름(FR-017)은 그대로 재사용한다.
* Physical Metadata의 정확한 저장 형식, 모듈 배치, 캐시 방식과 갱신 방식은 이 Spec의 동작을 바꾸지 않는 Plan 단계의 기술 결정이다.
* 대상 MSSQL Driver 선택은 Plan 단계의 기술 결정이다.
* DB Query Timeout과 Maximum Returned Rows의 구체적인 값은 이 Spec이 요구하는 강제 동작을 바꾸지 않는 Plan 또는 설정 단계의 결정이다.
* 이 Feature가 구성하는 Physical Metadata Catalog는 특정 DB 제품에 종속되지 않는 범용 다중 DB Metadata Import Platform으로 범위를 확장하지 않는다.

## 미결정 사항

이 Feature의 요구사항 자체에는 Plan 작성을 막는 미결정 사항이 없다. 다만 다음 두 종류는 구분해서 남긴다.

Plan 단계 기술 결정(요구사항을 바꾸지 않는 구현 선택):

* Physical Metadata Catalog의 정확한 저장 형식, 저장 위치, 캐시 구조와 갱신 방식.
* 대상 MSSQL Driver 선택.
* DB Query Timeout과 Maximum Returned Rows의 구체적인 값.

관련 기준 상태:

* `inspect_schema`와 `execute_readonly_query` Contract는 이 Spec과 함께 승인됐다.
* ADR-0001과 ADR-0007은 이 Spec과 함께 `Accepted`로 확정됐다.

## 검토 기록

Codex 검토 결과와 사용자 결정, 재검토 완료 상태를 기록한다.

| Reviewer | 발견 사항 → 결정 | 심각도 | 상태 |
|---|---|---|---|
| Codex | `inspect_schema` 결과만으로 끝나 Physical Metadata Catalog의 실제 구성이 요구되지 않음 → Backend가 애플리케이션용 Catalog를 실제 구성하는 요구사항(FR-007)으로 수정 | High | Resolved |
| Codex | `inspect_schema` Contract가 없고 `execute_readonly_query` Contract의 구현 시점이 이전 Week 2 Roadmap 기준임 → `inspect_schema` Contract 신규 작성, 기존 Contract를 FEAT-0003 기준으로 수정 | High | Resolved |
| Codex | FEAT-0003·0004의 단계적 구현 범위와 ADR-0007의 전체 Governance 선적용 표현이 충돌함 → ADR-0007에 Week 1 최소 안전 경계와 Week 2 전체 Governance 적용 순서를 기록 | Medium | Resolved |
| Codex | 대상 DB 환경설정과 연결 준비 실패 동작이 요구사항에 명시되지 않음 → 기존 `TARGET_DB_*` 환경변수를 재사용하고 설정·연결 준비 실패를 Fail Closed 요구사항(FR-017, FR-018)으로 추가 | Medium | Resolved |
| Codex | `row_count`의 "실제 행 수" 표현과 Timeout의 "강제 중단" 표현이 과도하거나 모호함 → `row_count`는 실제 반환 행 수로, Timeout은 "강제 중단" 대신 "DB Query Timeout 적용"으로 명확화 | Low | Resolved |
| Codex | ADR-0007이 Week 1 최소 Audit과 15개 규칙 전체 적용을 요구해 현재 Roadmap과 충돌함 → 실제 Workflow Audit은 Week 2 FEAT-0006으로 명확히 하고 Week 1에는 별도 Audit 구현을 요구하지 않음 | Medium | Resolved |
| Codex | `inspect_schema` Contract가 Startup 설정·연결 실패, Tool 실행 실패와 Transport 종료를 모두 MCP Tool 오류로 혼합함 → Startup·Tool 실행·Transport 실패로 구분 | Medium | Resolved |
| Codex | Spec 시나리오에 `row_count`가 전체 결과 건수처럼 보일 수 있는 "실제 행 수" 표현이 남아 있음 → "실제 반환된 행 수"로 수정 | Low | Resolved |
| Codex | `inspect_schema` JSON 예시의 FK Source Table이 `schemas` 결과에 없음 → Source Table을 예시에 포함하고 Summary를 맞추며 축약 예시의 경계를 명시 | Low | Resolved |
| Codex | 실제 AdventureWorks2022의 Table·Column `MS_Description`을 `data_agent_ro`로 읽을 수 있으나 Contract와 Spec에 포함되지 않음 → nullable 설명 필드를 Physical Metadata로 추가하고 자동 해석·Business Metadata 승격은 금지 | Medium | Resolved |
| Codex | `execute_readonly_query` Contract가 Week 1에도 전체 SQL Guardrail과 Plan-SQL Match 완료를 전제해 단계적 Roadmap과 충돌함 → 현재 단계에 요구되는 사전 검증으로 일반화하고 전체 검증은 FEAT-0006부터 적용한다고 명시 | Medium | Resolved |
| Codex | Spec이 의존하는 두 Tool Contract와 ADR-0001·ADR-0007이 초안 상태로 남아 승인 기준이 불일치함 → 사용자 승인에 따라 Contract와 ADR을 함께 `Accepted`로 확정 | Medium | Resolved |

## 관련 기준 문서

* 프로젝트 원칙: [README](../../../README.md)
* MVP 범위: [MVP Scope](../../mvp/scope.md)
* MVP 로드맵: [MVP Roadmap](../../mvp/roadmap.md)
* MVP 완료 기준: [MVP Acceptance Criteria](../../mvp/acceptance-criteria.md)
* Architecture: [전체 아키텍처](../../architecture/overview.md)
* Architecture: [컴포넌트 책임과 경계](../../architecture/component-boundaries.md)
* Architecture: [질문 처리 시퀀스](../../architecture/query-execution-sequence.md)
* Architecture: [프로젝트 모듈 구조](../../architecture/project-structure.md)
* Contract: [`inspect_schema`](../../contracts/inspect-schema.md)
* Contract: [`execute_readonly_query`](../../contracts/execute-readonly-query.md)
* ADR: [0001 Read-Only Target Database Access](../../adr/0001-readonly-db.md) (`Accepted`)
* ADR: [0007 Local stdio MCP DB Boundary](../../adr/0007-local-stdio-mcp-db-boundary.md) (`Accepted`)
