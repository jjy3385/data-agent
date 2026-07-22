# MVP 범위와 대표 시나리오 (MVP Scope)

> 이 문서는 3주 MVP에서 구현할 업무 범위, 대표 질문, 테스트 역할과 의도적으로 제외한 기능을 정의한다. 새로운 요구사항이 들어왔을 때 지금 구현할지 Post-MVP로 미룰지 판단하는 기준이다.

## 대표 테스트 환경

MVP는 로컬 Docker SQL Server에 복원한 `AdventureWorks2022` 단일 데이터베이스를 기준으로 검증한다.

* `Sales`: 최근 판매수요
* `Production`: 품목, 안전재고, 창고별 재고
* `Purchasing`: 공급업체, 조달 리드타임, 구매 거부 이력

AdventureWorks2022는 하나의 물리 DB지만 서로 다른 업무 모듈에 흩어진 데이터를 하나의 업무 맥락으로 조합하는 과정을 검증하는 데 사용한다. 다중 DB 인스턴스와 이기종 시스템 통합은 MVP 필수 범위가 아니다.

상세 스키마는 [AdventureWorks2022 Schema](../data/adventureworks2022-schema.md)를 참고한다.

MVP는 `inspect_schema` MCP Tool로 대상 DB의 Physical Metadata를 수집해 애플리케이션과 데모 웹 UI에서 사용할 Catalog로 구성한다. 업무 의미, 계산 기준과 승인 Join은 자동 추론하지 않고 관리자가 승인한 Business Metadata로 별도 관리한다.

## 대표 업무 질문

> 최근 판매와 재고·공급 상황을 함께 봤을 때 우선 확인해야 할 품목을 알려줘.

사용자는 내부 스키마, 지표 공식이나 Join을 알 필요가 없다. LLM은 질문을 런타임에 해석하고 ACL로 허용된 관리자 승인 Metadata를 조합하여 QueryPlan과 MSSQL을 생성한다. 사용자가 기간이나 계산 기준을 명시하지 않으면 승인된 기본값을 사용하고 적용한 기간, 계산식과 데이터 기준일을 XAI 설명에 표시한다.

MVP는 특정 문장을 고정 SQL에 연결하지 않는다. 범용성은 등록되고 승인된 Metadata의 조합 범위로 제한한다.

시나리오 선정 근거와 대안은 [MVP 시나리오 후보](scenario-candidates.md)를 참고한다.

## 테스트 역할과 ACL

| 역할 | 허용 범위 | 대표 질문 처리 |
|---|---|---|
| `supply_risk_analyst` | 품목·재고, 판매수요 집계, 공급업체와 구매 품질 요약 | 전체 2-Depth 분석 허용 |
| `inventory_viewer` | 품목과 재고 | 판매·구매 Metadata를 Context에서 제외하고 SQL 생성 전에 거부 |

부분 정보만으로 완전한 공급 리스크 분석처럼 보이는 답변을 만들지 않도록 `inventory_viewer`의 대표 질문은 Fail Closed 처리한다.

## MVP LLM Provider 정책

MVP는 하나의 설정된 LLM Provider만 사용한다. Provider 전환과 배포 형태별 동작 검증은 Post-MVP 범위다.

```dotenv
LLM_PROVIDER=<provider>
LLM_MODEL=<model-name>
LLM_API_KEY=<api-key>
LLM_BASE_URL=<optional-endpoint>
```

MVP는 LLM 배포 형태에 따라 결과 전달 경로를 분기하지 않는다. Depth 2 판단에는 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 Bounded Result를 Result Handle 없이 LLM에 직접 전달한다. Post-MVP의 배포 모드별 Direct·Handle 전략은 [ADR 0006](../adr/0006-result-handle.md)을 따른다.

## ACL-scoped Metadata Retrieval

Metadata Retrieval은 검증된 RuntimeIntent를 입력으로 관련 Metadata 후보를 찾고 현재 사용자 ACL과 교집합을 구한다. Query Planner에는 Retrieval을 통과한 Entity, Dimension, Metric, Time Policy, Join과 물리 매핑만 전달한다.

MVP는 소규모 승인 Catalog를 Alias·Keyword로 검색한다. 검색 결과가 없거나 정의가 충돌하면 명확화를 요청하거나 Fail Closed 처리한다. Vector Search 기반 Schema RAG와 자동 Metadata 추론은 Post-MVP다.

## 범용성 경계

허용되는 동작:

* 등록된 Entity, Dimension과 Metric 선택 및 조합
* 허용 범위 안의 Filter와 기간 Parameter 적용
* 승인된 Join을 이용한 테이블 연결
* Grouping, Ordering과 TOP N 구성
* 질문과 Depth 1 결과에 따른 최대 2-Depth QueryPlan 생성

허용되지 않는 동작:

* 등록되지 않은 Metric, 계산식 또는 업무 정의 생성
* Raw Schema 컬럼명이나 일반 업무 상식만으로 단위·집계 Grain 추론
* 승인되지 않은 Join 생성
* ACL에서 제외된 Metadata 사용
* Metadata가 부족한 상태에서 임의 SQL 생성

필요한 Metadata가 없으면 사용자에게 기준을 명확히 요청하거나 Fail Closed 처리한다. MVP는 고정 리포트 실행기도, 임의 기업 DB를 스스로 해석하는 범용 Semantic Engine도 아니다.

## 단계별 시연 범위

* Week 1은 대표 재고 질문 하나가 자연어 입력에서 Read-Only 조회 결과까지 이어지는 Depth 1 Walking Skeleton과 Jinja2 기반 데모 웹 UI를 완성한다. 사용자별 정책을 대신하는 고정 Demo Scope와 최소 실행 제한을 적용한다.
* Week 2는 Admin DB의 사용자·역할·Table Policy를 실제 요청 흐름에 적용하고 검증·Guardrail·실패 처리를 완성한 뒤 단일 EC2와 EBS 기반 AWS 데모 환경에 배포한다.
* Week 3은 대표 공급 위험 질문에 필요한 Business Metadata를 확장하고 최대 Depth 2 Workflow와 XAI 응답을 완성한다.

Jinja2 기반 데모 웹 UI는 자연어 질문과 결과, 등록된 Metadata, 승인된 AdventureWorks Sample 데이터를 읽기 전용으로 보여준다. 임의 SQL 입력, Metadata 편집과 범용 데이터 탐색 기능은 제공하지 않는다. 대상 DB 조회는 웹 UI나 FastAPI의 직접 연결이 아니라 승인된 MCP Tool을 통해서만 수행한다.

## 승인된 MVP 업무 Metadata

아래 정의는 관리자가 검토하고 승인한 MVP 업무 Metadata다. LLM은 질문에 맞는 Metadata를 선택하고 조합할 수 있지만 기간, 공식, 단위, 집계 Grain 또는 Join 의미를 새로 만들 수 없다.

MVP Metadata Catalog는 다음 종류의 정보를 중앙에서 관리한다.

* Business Table Name과 Business Column Name
* Code Dictionary
* Entity와 Dimension
* Business Metric과 계산식
* 기본 기간, 집계 Grain, 단위와 허용 Parameter
* 승인된 Physical FK와 Virtual FK
* ACL과 Sensitive Data Metadata
* 사용 제한과 XAI 표시 규칙

| 업무 용어 | MVP 정의 |
|---|---|
| 판매 기준일 | `Sales.SalesOrderHeader.OrderDate`의 최댓값 |
| 최근 90일 판매수요 | 판매 기준일부터 90일 이내의 `Sales.SalesOrderDetail.OrderQty` 합계 |
| 재고 | `Production.ProductInventory.Quantity`의 품목별 합계 |
| 안전재고 미달 | 품목별 재고 합계 `< Production.Product.SafetyStockLevel` |
| 공급업체 수 | 품목별 `Purchasing.ProductVendor`의 등록 공급업체 수 |
| 조달 리드타임 | `Purchasing.ProductVendor.AverageLeadTime` |
| 구매 거부 이력 | `Purchasing.PurchaseOrderDetail.RejectedQty` 집계 |

적용 원칙:

* “최근”의 기본 기간, 집계 Grain, 공식과 단위는 승인 Metadata에서 가져온다.
* Join은 검증된 Physical FK 또는 관리자가 정의·승인한 Virtual FK만 사용한다.
* 사용자가 다른 기간을 명시하면 허용된 Parameter 범위 안에서만 대체한다.
* `ProductInventory`를 일별 재고 스냅샷으로 해석하지 않는다.
* 도메인별 마지막 데이터 시점과 적용한 기본값을 XAI에 표시한다.

## Non-Goals

* Next.js 기반 Full Admin Portal
* Slack 연동
* SQL Self-Healing
* 다중 LLM Provider 전환과 배포 형태별 검증
* Metadata·사용자·정책 편집 UI
* 범용 Data Explorer와 임의 SQL Console
* Error Report 관리 Workflow와 UI
* CI/CD와 IaC
* 다중 인스턴스 운영 구성
* 다중 데이터 소스와 이기종 DB 통합
* 완전한 회원가입과 Auth 시스템
* 모든 Legacy DB를 자동 해석하는 범용 Semantic Engine
* 수요예측, 품절 예상일 계산과 자동 발주
* 다단계 BOM 영향 분석
* 무제한 자율 데이터 분석 Agent

## Post-MVP 후보

* Slack 입력·응답 Adapter
* Guardrail을 다시 통과하는 실행당 최대 1회의 SQL Self-Healing
* 다중 LLM Provider 전환 검증
* Error Report 관리 Workflow와 UI
* Formula·Aggregation·Grain Semantic Validation
* 3-Depth 이상 복합 조사와 다중 데이터 소스 Orchestration
* Schema RAG, Semantic Caching과 Metadata Import Assistant
* External 모드용 Result Store와 Result Handle 전달 경로
* ERP, MES, Groupware 스타일의 패키지형 Enterprise Solution MSSQL 추가 검증
* `EMP_NO`, `DEPT_CD`, `REG_DT` 같은 명명 규칙과 물리 FK가 없는 한국형 Legacy MSSQL 추가 검증

Post-MVP LLM 배포 모드별 결과 전달 전략은 [ADR 0006](../adr/0006-result-handle.md)을 따른다.
