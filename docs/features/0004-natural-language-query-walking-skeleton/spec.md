# 자연어 질문 처리 최소 동작 흐름 (Walking Skeleton) Spec

* Feature ID: `FEAT-0004`
* Status: `Approved`
* Development Track: `Standard`
* Track 선택 근거: LLM Provider 연결, RuntimeIntent·Business Metadata·QueryPlan·SQL 생성과 검증, FEAT-0003 MCP 실행 경계 재사용을 잇는 여러 컴포넌트의 새로운 호출 흐름과 Fail Closed 경계를 포함하므로 Standard Track을 적용한다.
* Roadmap: [Week 1 - FEAT-0004 자연어 질문 처리 최소 동작 흐름](../../mvp/roadmap.md#week-1-local-depth-1-demo)

## 목적

대표 재고 질문 하나("현재 재고가 안전재고보다 부족한 제품을 보여줘")가 자연어 HTTP 요청에서 실제 AdventureWorks2022 조회 결과까지 실제로 이어지는 Depth 1 Walking Skeleton을 만든다. RuntimeIntent 생성 → 최소 Business Metadata 선택 → Metadata Context 구성 → QueryPlan 생성·검증 → MSSQL 생성 → 최소 실행 제한 검증 → FEAT-0003 MCP 실행 경계를 통한 실제 조회 → Bounded Result 응답이라는 흐름 전체를 하나의 대표 질문에 대해 실제로 연결하는 것이 목표이며, 이 자연어를 고정 SQL에 매핑하는 것이 아니다.

이 대표 질문은 `Production.ProductInventory`에 재고 행이 하나 이상 있는 제품만 대상으로 하고, 그 행들의 위치별 `Quantity`를 `ProductID` 단위로 합산한 값을 현재 재고로 판단한다. `Production.ProductInventory` 행이 없는 제품은 이 모집단에서 제외하며, 그런 제품에 대해 재고 0 값을 생성하거나 안전재고와 비교하지 않는다. 합산 값이 `Production.Product.SafetyStockLevel`보다 작은 제품을 안전재고 미달로 판단한다.

이 Feature는 사용자별 ACL, 전체 SQL Guardrail·Plan-SQL Match, Audit, Depth 2와 XAI를 완성하지 않는다. 이런 완전한 안전·설명 경계는 FEAT-0006 이후에 이 Walking Skeleton 위에 적용된다.

## 범위

포함:

* [자연어 질문 API Contract](../../contracts/natural-language-query.md)를 따르는 HTTP API와 요청마다 발급해 처리 단계·모든 응답에서 사용하는 Correlation ID
* 설정된 단일 LLM Provider 연결과 설정 없음·유효하지 않음에 대한 Fail Closed 동작
* [RuntimeIntent Contract](../../contracts/runtime-intent.md)를 따르는 RuntimeIntent 생성과 최소 검증
* 대표 재고 질문에 필요한 최소 Business Metadata(재고 대상·집계·미등록 제품 처리 정책 포함)와 고정 Demo Scope
* 검증된 RuntimeIntent를 기준으로 한 최소 Metadata Context 구성
* [QueryPlan Contract](../../contracts/query-plan.md)를 따르는 Depth 1 QueryPlan 생성과 최소 검증
* 검증된 QueryPlan과 제한된 Metadata Context를 사용한 MSSQL 생성과 최소 실행 제한(결정적인 `ORDER BY` 강제 포함)
* FEAT-0003의 MCP 실행 경계(MCPClientManager, `execute_readonly_query`, Physical Metadata Catalog)를 통한 실제 조회와 TOP N·Maximum Returned Rows가 적용된 Bounded Result의 HTTP JSON 응답
* 대표 질문의 Golden Query 검증과, 의미상 동등하지만 표현이 다른 한국어 질문이 같은 기준 결과로 이어지는지 확인하는 검증 요구사항
* 자연어 질문 접수부터 실제 MSSQL 조회 결과까지의 End-to-End 검증 요구사항

제외:

* Jinja2 데모 웹 UI(FEAT-0005)
* Admin DB 사용자·역할·Table Policy 기반 ACL(FEAT-0006)
* 완전한 RuntimeIntent·QueryPlan Validation(Formula·Aggregation·Grain 등 의미 검증)
* SQL AST 기반 전체 Guardrail과 구조적 Plan-SQL Match(FEAT-0006)
* Audit과 Error Report 연결(FEAT-0006)
* AWS 배포(FEAT-0007)
* 판매·공급업체까지 포함하는 Business Metadata 확장(FEAT-0008)
* Depth 2, Next Action, Drill Down(FEAT-0009)
* XAI 최종 설명(FEAT-0010)
* Slack 연동, SQL Self-Healing, Result Store와 Result Handle, 다중 LLM Provider
* FastAPI의 대상 DB 직접 연결, 자연어를 고정 SQL에 단순 매핑하는 구현, 임의 SQL을 입력받아 실행하는 API
* Business Metadata 편집 UI 또는 승인 Workflow

이 Feature는 FEAT-0003이 제공하는 MCP 실행 경계를 재사용해 자연어 질문에서 Depth 1 결과까지 연결한다. FEAT-0006은 이 흐름 위에 실제 사용자 ACL과 전체 Validation·Guardrail·Audit을 적용한다.

## 사용자 또는 시스템 시나리오

### 시나리오 1: 대표 재고 질문이 실제 조회 결과로 이어진다

* Given: [자연어 질문 API Contract](../../contracts/natural-language-query.md)를 구현한 HTTP API, 설정된 LLM Provider, 최소 Business Metadata와 FEAT-0003의 MCP 실행 경계가 준비되어 있다.
* When: 사용자가 "현재 재고가 안전재고보다 부족한 제품을 보여줘"를 API로 전송한다.
* Then: 시스템은 Correlation ID를 발급하고 RuntimeIntent 생성·검증, Metadata Context 구성, QueryPlan 생성·검증, MSSQL 생성·최소 실행 제한 검증을 거쳐 FEAT-0003의 `execute_readonly_query`로 실제 AdventureWorks2022를 조회한다. 응답은 `status: "completed"`이며, 재고 행이 있는 제품 중 안전재고보다 부족한 제품만 `ProductID` 오름차순으로 포함하고 각 행은 제품 ID·제품명과 현재 재고·안전재고 값을 포함하는 Bounded Result다.

### 시나리오 2: Golden Query와 표현이 다른 동등한 질문도 같은 결과로 이어진다

* Given: 대표 질문에 대해 사람이 검토·승인한 Golden Query 하나와 기준 결과가 있다. 이 Golden Query는 재고 행이 있는 제품만 대상으로 위치별 `Quantity`를 `ProductID` 단위로 합산하고 `ProductID` 오름차순으로 정렬한다.
* When: 대표 질문과 의미상 동등한 다음 세 질문을 각각 시스템에 전송한다: "현재 재고가 안전재고보다 부족한 제품을 보여줘.", "안전재고 기준에 미달한 품목을 알려줘.", "창고별 수량을 합쳤을 때 최소 재고보다 적은 상품은?".
* Then: 세 질문 모두 고정 SQL에 매핑되지 않고 RuntimeIntent → Metadata Context → QueryPlan → SQL 흐름을 실제로 거친다. 각 질문의 RuntimeIntent 문구나 생성된 SQL 문자열이 완전히 같을 필요는 없지만, 최종 제품 집합·`ProductID` 순서·현재 재고·안전재고 값은 모두 같은 Golden Query 기준과 일치한다.

### 실패 동작

실행 전 검증에 실패한 요청은 해당 단계에서 멈추며 SQL을 실행하지 않는다. MCP 실행 실패와 내부 실패는 실행을 시도한 이후 발생할 수 있지만 Bounded Result를 반환하지 않는다. 응답의 정확한 필드는 [자연어 질문 API Contract](../../contracts/natural-language-query.md)를 따른다.

| 실패 지점 | 응답(`status`/`code`) | SQL 실행 여부 |
|---|---|---|
| 요청 자체가 Contract를 만족하지 않음(`question` 비어 있음, 정의되지 않은 추가 필드) | `rejected` / `invalid_request` | 미실행 |
| 설정된 LLM Provider가 없거나 비어 있거나 유효하지 않음 | `failed` / `llm_unavailable` | 미실행 |
| RuntimeIntent가 Contract를 만족하지 못함 | `rejected` / `intent_contract_violation` | 미실행 |
| RuntimeIntent가 명확화를 요구함(`requires_clarification=true`) | `clarification_required` / `clarification_required` | 미실행 |
| 필요한 Business Metadata가 없거나 고정 Demo Scope를 벗어남 | `rejected` / `metadata_not_found` | 미실행 |
| QueryPlan이 Metadata Context 밖을 참조하거나 `depth`가 1이 아니거나 Demo Scope를 벗어남 | `rejected` / `query_plan_invalid` | 미실행 |
| SQL이 SELECT-only·허용 Table·Column·TOP N·결정적 `ORDER BY` 중 하나라도 위반함 | `rejected` / `sql_rejected` | 미실행 |
| 정상 시작 이후 요청 처리 중 MCP Call Timeout·연결 종료·Tool 오류 발생 | `failed` / `mcp_execution_failed` | 실행 시도 후 실패 |
| 위 범주로 분류할 수 없는 예상하지 못한 내부 실패 | `failed` / `internal_error` | 상황에 따라 다름(원본 노출 없음) |

FastAPI Startup 단계의 MCP 초기화·Tool Discovery·Tool Contract 검증·`inspect_schema`·Physical Metadata Catalog 구성 실패는 이 표에 포함하지 않는다. 그 경우 FEAT-0003의 기존 Fail Closed 경계에 따라 ASGI Startup 자체가 완료되지 않아 이 HTTP API가 요청을 받지 않으며, `mcp_execution_failed`로 표현하지 않는다.

## 기능 요구사항

* `FR-001`: 시스템은 [자연어 질문 API Contract](../../contracts/natural-language-query.md)의 요청 구조를 따르는 HTTP API를 제공해야 하며, 요청마다 Correlation ID를 발급해 RuntimeIntent 생성부터 최종 응답(성공·명확화·거부·실패)까지 모든 단계와 응답에서 동일하게 사용해야 한다.
* `FR-002`: 시스템은 `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL` 설정으로 식별되는 단일 LLM Provider를 사용해 자연어 질문을 [RuntimeIntent Contract](../../contracts/runtime-intent.md)를 만족하는 RuntimeIntent로 구조화해야 한다. 필수 설정이 없거나 비어 있거나 유효하지 않으면 자연어 질문을 정상적으로 처리하지 않고 `failed`/`llm_unavailable` 응답으로 안전하게 실패해야 하며, 이 경우 어떤 SQL도 생성·실행하지 않아야 한다.
* `FR-003`: 시스템은 생성된 RuntimeIntent가 RuntimeIntent Contract를 만족하는지 검증해야 하며, Contract를 만족하지 않거나 `requires_clarification`이 `true`로 표시되면 이후 Metadata Retrieval과 QueryPlan·SQL 생성으로 진행하지 않아야 한다.
* `FR-004`: 시스템은 대표 재고 질문에 필요한 최소 Business Metadata를 관리하고 Week 1 동안 사용자별 Admin DB ACL 대신 고정 Demo Scope(최소 Business Metadata와 그에 대응하는 허용 Table·Column)를 실행 허용 범위로 사용해야 한다. 최소 Business Metadata에는 다음이 포함되어야 한다: 제품(제품 ID·제품명 Dimension 포함), 제품별 현재 재고(`Production.ProductInventory`에 재고 행이 하나 이상 있는 제품만 대상으로 그 행들의 위치별 `Quantity`를 `ProductID` 단위로 합산한 값이며, 행이 없는 제품은 이 모집단에서 제외하고 재고 0 값을 생성하거나 안전재고와 비교하지 않는다), 안전재고(`Production.Product.SafetyStockLevel`), 안전재고 부족을 판정하는 승인 Filter, `Production.Product`와 `Production.ProductInventory` 사이의 승인된 Physical FK.
* `FR-005`: 시스템은 검증된 RuntimeIntent를 검색 입력으로 사용해 고정 Demo Scope 안의 최소 Business Metadata만 선택한 Metadata Context를 구성해야 한다. 필요한 Business Metadata를 찾지 못하거나 질문이 고정 Demo Scope를 벗어나면 QueryPlan과 SQL을 생성·실행하지 않고 `rejected`/`metadata_not_found` 응답을 반환해야 한다. 명확화가 필요한 요청은 이 단계에 도달하기 전에 RuntimeIntent 검증 단계에서 `clarification_required`/`clarification_required`로 중단해야 한다.
* `FR-006`: 시스템은 LLM이 Metadata Context에 포함된 승인 Metadata만 참조하는 [QueryPlan Contract](../../contracts/query-plan.md)를 만족하는 Depth 1 QueryPlan을 생성하도록 해야 한다. Backend는 참조 Metadata의 존재 여부, `depth=1` 여부와 고정 Demo Scope 허용 범위를 검증해야 하며, 검증에 실패하면 SQL을 생성하지 않아야 한다.
* `FR-007`: 시스템은 검증된 QueryPlan과 제한된 Metadata Context를 사용해 LLM이 단일 SELECT MSSQL Statement를 생성하도록 해야 한다. 실행 전에 SELECT-only 여부, 허용된 Table·Column 범위, TOP N 존재와 결정적인 `ORDER BY` 존재를 포함한 최소 실행 제한을 검증해야 하며, `ORDER BY`가 없거나 고정 Demo Scope 밖의 정렬 항목을 사용하는 경우를 포함해 검증에 실패하면 SQL을 실행하지 않아야 한다.
* `FR-008`: 시스템은 최소 실행 제한을 통과한 SQL을 FEAT-0003의 MCPClientManager와 `execute_readonly_query` Tool을 통해서만 실행해야 하며, FastAPI가 대상 DB에 직접 연결해 실행하지 않아야 한다. MCP 실행 결과에서 TOP N과 Maximum Returned Rows가 적용된 Bounded Result를 [자연어 질문 API Contract](../../contracts/natural-language-query.md)의 `completed` 응답 구조로 반환해야 하며, 기본 정렬은 `ProductID` 오름차순이고 동일한 데이터에서는 항상 같은 순서로 결과를 반환해야 한다.
* `FR-009`: 시스템은 LLM이 생성한 RuntimeIntent, QueryPlan과 SQL을 그대로 신뢰하지 않아야 하며, 각 단계에서 Backend가 검증한 뒤에만 다음 단계로 진행해야 한다.
* `FR-010`: 이 Feature는 대표 재고 질문에 대해 사람이 검토하고 승인한 Golden Query 하나와 기준 결과를 가지고 있어야 하며, 다음을 검증할 수 있어야 한다: (1) 자연어 흐름으로 얻은 결과의 제품 집합·순서·핵심 값(제품, 현재 재고, 안전재고)이 이 Golden Query 기준과 일치하는지, (2) 대표 질문과 의미상 동등하지만 표현이 다른 세 질문("현재 재고가 안전재고보다 부족한 제품을 보여줘.", "안전재고 기준에 미달한 품목을 알려줘.", "창고별 수량을 합쳤을 때 최소 재고보다 적은 상품은?")이 각각 고정 SQL에 매핑되지 않고 실제 흐름을 거쳐 같은 Golden Query 기준과 일치하는 결과를 반환하는지(모든 한국어 동의어 등록을 요구하는 것은 아니며, 판매·공급업체 등 Demo Scope 밖 질문은 `FR-005`에 따라 `rejected`/`metadata_not_found`로 거부한다), (3) 자연어 질문 접수부터 FEAT-0003의 MCP 실행 경계를 통한 실제 AdventureWorks2022 조회 결과 반환까지 전체 흐름이 실제로 연결되어 동작하는지(End-to-End).

## 비기능 요구사항

* `NFR-001`: 이 Feature는 FastAPI가 대상 DB 드라이버를 사용하거나 대상 DB에 직접 연결하지 않아야 하며, 대상 DB 접근은 FEAT-0003의 MCP 실행 경계만 사용해야 한다.
* `NFR-002`: 이 Feature는 하나의 설정된 LLM Provider만 지원해야 하며, Provider 전환이나 다중 Provider 동시 지원을 구현하지 않아야 한다.
* `NFR-003`: 이 Feature는 자연어 질문을 고정 SQL에 직접 매핑하지 않아야 하며, 정상적으로 실행되는 요청은 RuntimeIntent → Metadata Context → QueryPlan → SQL 흐름을 실제로 거쳐야 한다. Week 1은 고정 Demo Scope에 필요한 최소 실행 제한만 적용하며, SQL AST 기반 전체 Guardrail과 구조적 Plan-SQL Match는 FEAT-0006에서 완성한다. 검증에 실패한 요청에는 QueryPlan이나 SQL 생성을 강제하지 않아야 한다.
* `NFR-004`: [자연어 질문 API Contract](../../contracts/natural-language-query.md)가 정의하는 어떤 응답에도 원본 Prompt 전문, LLM 원문 오류 메시지, 대상 DB Driver 원문 오류 메시지, 대상 DB 자격 증명이나 내부 Stack Trace를 노출하지 않아야 한다. 이 Contract가 정의한 오류 범주로 분류할 수 없는 예상하지 못한 내부 실패는 원본 Exception이나 구현 정보를 노출하지 않고 `status: "failed"`, `code: "internal_error"`의 고정된 안전 메시지로 표현해야 한다.
* `NFR-005`: 이 Feature는 FEAT-0003의 MCP Startup Fail Closed 경계(MCP Server 초기화, Tool Discovery, Tool Contract 검증, Startup 시 `inspect_schema` 호출, Physical Metadata Catalog 구성)를 다시 설계하지 않고 그대로 재사용해야 한다. 이 경계가 실패하면 ASGI Startup이 완료되지 않으며, 이 실패를 자연어 질문 API의 `mcp_execution_failed` HTTP 응답으로 표현하지 않아야 한다. `mcp_execution_failed`는 정상적으로 시작된 이후 요청을 처리하는 도중 발생하는 MCP Call Timeout, 연결 종료, Tool 오류 또는 DB Query Timeout에만 사용해야 한다.

## Acceptance Criteria

* [ ] 자연어 질문 API가 Contract 요청 구조로 대표 질문을 접수하며, `question`이 비어 있거나 정의되지 않은 추가 필드를 포함하면 `rejected`/`invalid_request`로 거부하고 그 값을 RuntimeIntent·QueryPlan·SQL 생성에 사용하지 않는다.
* [ ] 모든 응답(성공·명확화·거부·실패)이 Correlation ID를 포함하며, RuntimeIntent·Metadata Context·QueryPlan·SQL·MCP 실행 전체 단계가 같은 Correlation ID로 연결된다.
* [ ] 설정된 LLM Provider(`LLM_PROVIDER`/`LLM_MODEL`/`LLM_API_KEY`/필요 시 `LLM_BASE_URL`)가 없거나 유효하지 않으면 RuntimeIntent를 생성하지 않고 `failed`/`llm_unavailable`로 안전하게 실패하며 어떤 SQL도 생성·실행되지 않는다.
* [ ] LLM이 생성한 RuntimeIntent·QueryPlan·SQL은 각 단계에서 Backend 검증을 통과한 뒤에만 다음 단계로 진행되며, RuntimeIntent Contract 위반·명확화 필요·Business Metadata 없음·QueryPlan 검증 실패·SQL 최소 검증 실패는 각각 정의된 `rejected`/`clarification_required` 응답으로 SQL 생성·실행 전에 중단된다. QueryPlan의 정확한 필드와 불변조건은 [QueryPlan Contract](../../contracts/query-plan.md)를 따른다.
* [ ] 최소 Business Metadata는 제품(ID·제품명), `ProductInventory` 행이 있는 제품만 대상으로 위치별 `Quantity`를 `ProductID` 단위로 합산한 현재 재고(행이 없는 제품은 모집단에서 제외하며 재고 0 값을 생성하거나 비교하지 않음), 안전재고, 안전재고 부족 승인 Filter와 `Production.Product`·`Production.ProductInventory` 사이의 승인 FK를 포함한다.
* [ ] 검증된 SQL은 FEAT-0003의 MCPClientManager와 `execute_readonly_query`를 통해서만 실행되고 FastAPI가 대상 DB에 직접 연결하는 경로가 없으며, 성공 응답은 `status: "completed"`로 TOP N·Maximum Returned Rows가 적용된 Bounded Result를 `ProductID` 오름차순으로 포함한다.
* [ ] 정상적으로 시작된 이후 요청 처리 중 MCP 실행이 실패하면 대상 DB 직접 실행으로 우회하지 않고 `failed`/`mcp_execution_failed`를 반환한다. FastAPI Startup 단계의 MCP 초기화·Tool Discovery·Tool Contract 검증·`inspect_schema`·Physical Metadata Catalog 구성 실패는 이 응답이 아니라 FEAT-0003의 기존 Fail Closed 경계에 따라 ASGI Startup이 완료되지 않는 것으로 관찰된다.
* [ ] 대표 질문에 대해 검토·승인된 Golden Query 하나와 기준 결과가 있고, 의미상 동등하지만 표현이 다른 세 질문("...보여줘.", "...알려줘.", "...상품은?")이 각각 고정 SQL 매핑 없이 실제 흐름을 거쳐 같은 Golden Query 기준(제품 집합·순서·재고·안전재고 값)과 일치하며, 자연어 질문 접수부터 실제 AdventureWorks2022 MCP 조회 결과까지 End-to-End로 검증할 수 있다.
* [ ] 어떤 응답에도 원본 Prompt, LLM·Driver 원문 오류, 자격 증명이나 내부 Stack Trace가 노출되지 않으며, 분류할 수 없는 내부 실패는 `failed`/`internal_error`로 안전하게 표현된다.

## 가정과 제약

* FEAT-0003이 제공하는 MCPClientManager, `execute_readonly_query` Tool, FastAPI Lifespan 동안 유지되는 Physical Metadata Catalog와 MCP Startup Fail Closed 경계를 그대로 재사용하며, 대상 DB 연결·Read-Only 경계와 MCP 실행 경계 자체는 다시 정의하지 않는다([FEAT-0003 Spec](../0003-mcp-readonly-data-access/spec.md), [ADR 0001](../../adr/0001-readonly-db.md), [ADR 0007](../../adr/0007-local-stdio-mcp-db-boundary.md)).
* "재고"와 "안전재고 미달"의 업무 정의는 [MVP 범위](../../mvp/scope.md)의 승인된 MVP 업무 Metadata 표에 이미 정의되어 있으며, 이 Feature는 그 정의를 그대로 사용한다.
* Agent Workflow의 최대 Depth 제한 자체는 [ADR 0004](../../adr/0004-agent-depth.md)(현재 상태 `Proposed`)가 정의하며, 이 Feature는 Depth 1만 실행해 그 상한을 넘지 않는다. Depth 상한의 실제 강제와 ADR 승인은 이 Feature의 범위가 아니다.
* LLM 설정은 `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL` 네 이름을 사용한다([MVP 범위](../../mvp/scope.md), `.env.example`). `LLM_DEPLOYMENT_MODE`는 Post-MVP 결과 전달 정책([ADR 0006](../../adr/0006-result-handle.md)) 전용이며 이 Feature는 배포 모드에 따라 결과 전달 경로를 분기하지 않는다.
* AdventureWorks2022는 로컬 Docker SQL Server에 복원된 단일 DB를 기준으로 검증한다([MVP 범위](../../mvp/scope.md)). AWS 배포 환경에서의 동작은 이 Feature의 범위가 아니다.

## 미결정 사항

이 Feature의 요구사항과 범위 자체에는 Plan 작성을 막는 미결정 사항이 없다.

Plan 단계 기술 결정(요구사항을 바꾸지 않는 구현 선택): Business Metadata의 저장 형식·위치, RuntimeIntent·QueryPlan·SQL 생성에 사용할 Prompt 구성·LLM SDK·실제 모델 이름 값, `LLM_BASE_URL`을 포함해 어떤 LLM 설정이 Provider별로 선택적인지, 고정 Demo Scope의 표현 방식, HTTP 요청·응답의 정확한 경로·메서드·상태 코드(Contract의 `status`/`code` 매핑 포함), TOP N·DB Query Timeout·Maximum Returned Rows의 구체적인 값(FEAT-0003 Tool 입력 범위 안에서 결정), Golden Query 정의와 E2E 검증 수행 방식.

관련 기준 상태: `RuntimeIntent`, `QueryPlan`과 자연어 질문 API Contract는 이 Spec과 함께 `Accepted`로 승인됐다. `execute_readonly_query`와 `inspect_schema` Contract는 FEAT-0003과 함께 `Accepted` 상태이며 이 Feature는 두 Tool의 입력·출력 형식을 바꾸지 않는다. ADR-0001, ADR-0007과 ADR-0006(MVP 결정 부분)은 `Accepted` 상태다. ADR-0004는 `Proposed` 상태이지만 이 Feature는 Depth 1만 실행해 그 결정에 의존하지 않는다.

## 검토 기록

Codex 검토 결과와 반영 내용을 주제별로 병합해 기록한다(세부 발견 순서가 아니라 최종 결정을 기준으로 정리). 상태는 반영이 끝나면 `Resolved`, 아직 반영하지 않았으면 `재검토 대기`로 표시한다.

| Reviewer | 발견 사항 → 결정 | 심각도 | 상태 |
|---|---|---|---|
| Codex | 공개 Contract 구체화: RuntimeIntent·QueryPlan Contract가 개념 설명 수준이고 자연어 질문 HTTP API Contract가 없었음 → 세 Contract 모두 구현 가능한 JSON 구조, 필드 타입·필수 여부·Enum·불변조건과 대표 예시로 확정하고 Spec 전반과 연결 | High | Resolved |
| Codex | QueryPlan 구조와 불변조건: Metric·Filter ID 혼용, 결과 표시용 Dimension 누락, 자유 문자열 `grain`, `filters`/`order_by` 중첩 규칙과 `limit` 허용 범위 불완전 → `filters[].filter_id`로 Metric과 분리, `dimension_ids`에 `product_id`·`product_name` 명시, `grain_id`(`product`만 허용)로 교정, 배열 항목의 필드·타입·중복 금지 규칙과 `execute_readonly_query`의 `maximum_returned_rows` 범위 참조를 확정 | High | Resolved |
| Codex | 재고 모집단·집계 정책: `ProductInventory` 행이 없는 제품의 처리 의미가 모호했고 "재고 0으로 간주" 표현이 값을 계산한 뒤 비교에서 제외하는 것으로 오해될 수 있었으며 FEAT-0008 이후 정책 변경을 금지하는 것으로 읽힐 위험이 있었음 → 행이 없는 제품은 모집단에서 제외하고 재고 0 값을 생성하거나 비교하지 않는다는 의미로 목적·FR·Acceptance Criteria를 통일하고, 후속 Feature가 별도 요구사항으로 다른 재고 해석을 검토·승인할 수 있다고 명확화 | Medium | Resolved |
| Codex | API 오류와 MCP 실패 경계: `NFR-008`의 "모든 요청이 SQL까지 간다"는 표현이 실패 시나리오와 모순됐고, 요청의 정의되지 않은 추가 필드 처리가 모호했으며, 공개 오류 `code`를 Plan이 임의로 확장할 수 있다는 문장이 있었고, MCP Startup 실패와 정상 시작 후 요청 중 MCP 실행 실패가 `mcp_execution_failed` 하나로 혼합됐음 → 정상 요청만 전체 흐름을 거치고 실패 요청은 해당 단계에서 중단한다고 재작성, 추가 필드는 예외 없이 `invalid_request`로 거부, `code` Enum을 이 Contract가 정의하는 목록으로 고정하고 분류 불가 실패를 위한 `internal_error` 추가, Startup 실패(FEAT-0003의 기존 ASGI 미완료 경계 재사용)와 요청 중 실패(`mcp_execution_failed`)를 구분 | High | Resolved |
| Codex | Golden Query와 한국어 표현 변형: 표현이 다른 동등한 질문에 대한 LLM 실효성 검증 요구사항이 없었음 → Golden Query는 하나로 유지하면서 의미상 동등한 세 질문이 고정 SQL 매핑 없이 같은 Golden Query 결과와 일치하는지 검증하는 요구사항을 시나리오·`FR-010`·Acceptance Criteria에 추가 | Medium | Resolved |
| Codex | 실행 제한: TOP N에 결정적인 정렬 기준이 없었고 LLM 환경설정 이름이 `docs/mvp/scope.md`와 `.env.example` 사이에서 충돌했음 → `ORDER BY` 필수와 기본 정렬 `ProductID` 오름차순을 확정하고, `.env.example`을 `scope.md` 기준(`LLM_PROVIDER`/`LLM_MODEL`/`LLM_API_KEY`/`LLM_BASE_URL`)으로 정리하며 `LLM_DEPLOYMENT_MODE`(Post-MVP 전용)를 제거 | Medium | Resolved |
| Codex | Spec 축약: 약 266줄로 늘어난 Spec에서 재고 정책·MCP 실패 구분 같은 같은 결정이 목적·시나리오·FR·NFR·AC·가정과 제약에 반복됐고 검토 기록 19건이 개별 항목으로 나열돼 있었음 → 핵심 요구사항 손실 없이 실패 시나리오 7개를 표로, FR 19개를 10개로, NFR 11개를 5개로, AC 23개를 9개로 통합하고 검토 기록을 주제별 7건으로 병합. 외부 문서에 FEAT-0004의 FR/NFR 번호를 참조하는 곳이 없음을 확인한 뒤 순차 재번호화 | Medium | Resolved |
| Codex | 비성공 응답의 SQL 실행 여부: API Contract가 모든 `failed` 응답을 SQL 미실행으로 규정해 실행 시도 후 발생할 수 있는 `mcp_execution_failed`·`internal_error`와 충돌했고, Spec의 실패 표 도입 문장·명확화 `code`·Metadata 실패 응답도 불일치 → 실행 전 중단과 실행 시도 후 실패를 구분하고 모든 비성공 응답에서 Bounded Result를 금지하며, 명확화는 RuntimeIntent 단계의 `clarification_required`/`clarification_required`, Metadata 실패는 `rejected`/`metadata_not_found`로 통일 | High | Resolved |

## 관련 기준 문서

* 프로젝트 원칙: [README](../../../README.md)
* MVP 범위: [MVP Scope](../../mvp/scope.md)
* MVP 로드맵: [MVP Roadmap](../../mvp/roadmap.md)
* MVP 완료 기준: [MVP Acceptance Criteria](../../mvp/acceptance-criteria.md)
* Architecture: [질문 처리 시퀀스](../../architecture/query-execution-sequence.md)
* Architecture: [컴포넌트 책임과 경계](../../architecture/component-boundaries.md)
* Contract: [자연어 질문 API](../../contracts/natural-language-query.md)
* Contract: [RuntimeIntent](../../contracts/runtime-intent.md)
* Contract: [QueryPlan](../../contracts/query-plan.md)
* Contract: [`execute_readonly_query`](../../contracts/execute-readonly-query.md)
* Contract: [`inspect_schema`](../../contracts/inspect-schema.md)
* ADR: [0001 Read-Only Target Database Access](../../adr/0001-readonly-db.md) (`Accepted`)
* ADR: [0004 Agent Workflow 깊이 제한](../../adr/0004-agent-depth.md) (`Proposed`)
* ADR: [0006 Post-MVP LLM 배포 모드별 결과 전달 전략](../../adr/0006-result-handle.md) (`Accepted for MVP`)
* ADR: [0007 Local stdio MCP DB Boundary](../../adr/0007-local-stdio-mcp-db-boundary.md) (`Accepted`)
* Feature: [FEAT-0003 MCP Read-Only Data Access Spec](../0003-mcp-readonly-data-access/spec.md) (`Approved`)
