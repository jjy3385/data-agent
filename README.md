# B2B SQL Data Agent

> 관리자가 승인한 Metadata와 접근 정책을 기반으로 비개발자의 자연어 질문을 안전한 Read-Only SQL 조회와 설명 가능한 응답으로 연결하는 On-Premise Data Governance & Orchestration Layer입니다.

## 이 프로젝트가 해결하는 문제

ERP, MES, Groupware와 기존 MSSQL 기반 레거시 시스템의 데이터는 여러 업무 모듈과 화면에 흩어져 있습니다. 사용자는 내부 스키마, 지표 공식이나 Join을 알지 못해도 자연스러운 업무 언어로 질문할 수 있어야 합니다.

이 프로젝트는 LLM이 기업 DB를 직접 이해하거나 자유롭게 조회하도록 만들지 않습니다. 기업이 검증한 Metadata, ACL, Physical·Virtual FK, 데이터 사전과 실행 정책 안에서만 LLM을 사용합니다.

대표 MVP 질문은 다음과 같습니다.

> 최근 판매와 재고·공급 상황을 함께 봤을 때 우선 확인해야 할 품목을 알려줘.

상세 범위와 업무 정의는 [MVP 범위](docs/mvp/scope.md)를 참고합니다.

## 로컬 실행 및 Swagger 수동 테스트

### 사전 준비

로컬 실행에는 다음 항목이 필요합니다.

* Python 3.12 이상과 [uv](https://docs.astral.sh/uv/)
* Docker Desktop
* Microsoft ODBC Driver 18 for SQL Server
* 복원된 `AdventureWorks2022` 데이터베이스와 Read-Only 애플리케이션 계정
* JSON Mode를 지원하는 OpenAI 호환 LLM Provider 설정

SQL Server를 처음 준비한다면 [로컬 SQL Server 개발 환경](docker/mssql/README.md)의
백업 복원 및 애플리케이션 Read-Only 계정 절차를 먼저 완료합니다.

### 1. 환경변수 준비

저장소 루트에서 예제 파일을 복사해 `.env`를 만들고 실제 로컬 설정값을 입력합니다.

```bash
cp .env.example .env
```

필수 설정은 `MSSQL_SA_PASSWORD`, `TARGET_DB_*`, `LLM_PROVIDER`,
`LLM_MODEL`, `LLM_API_KEY`입니다. OpenAI 호환 Endpoint를 사용하는 Provider는
`LLM_BASE_URL`도 설정합니다. `.env`에는 비밀번호와 API Key가 포함되므로 Git에
추가하거나 문서, 이슈 및 채팅에 내용을 붙여넣지 않습니다.

### 2. SQL Server와 의존성 준비

```bash
docker compose up -d
docker compose ps
uv sync
```

`docker compose ps`에서 `data-agent-mssql`이 `Up` 상태인지 확인합니다. 데이터베이스를
최초로 복원해야 하거나 컨테이너가 정상 기동하지 않으면
[SQL Server 실행 가이드](docker/mssql/README.md)를 참고합니다.

### 3. FastAPI 서버 실행

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

FastAPI Startup 과정에서 Admin DB를 준비하고 로컬 `stdio` MCP Server를 시작한 뒤,
대상 DB의 Physical Metadata를 검사합니다. 대상 DB 연결이나 Metadata 검증이 실패하면
안전하지 않은 상태로 요청을 받지 않고 Startup이 실패합니다.

서버가 준비되면 다음 주소를 확인합니다.

* Swagger UI: <http://localhost:8000/docs>
* 상태 확인: <http://localhost:8000/health>

`GET /health`의 정상 응답은 다음과 같습니다.

```json
{
  "status": "ok"
}
```

### 4. Swagger에서 자연어 질문 실행

1. Swagger UI에서 `POST /api/questions`를 펼칩니다.
2. **Try it out**을 선택합니다.
3. 다음 Request body를 입력하고 **Execute**를 선택합니다.

```json
{
  "question": "현재 재고가 안전재고보다 부족한 제품을 보여줘"
}
```

정상 처리되면 HTTP 200 응답의 `status`가 `completed`이고, `bounded_result`에
`ProductID`, `Name`, `CurrentInventory`, `SafetyStockLevel` 조회 결과가 포함됩니다.
이 API는 자연어 질문만 받으며 SQL, RuntimeIntent, QueryPlan 또는 DB 연결 설정을
Request body에 추가하면 `rejected`/`invalid_request`로 거부합니다.

응답 상태의 의미는 다음과 같습니다.

| `status` | 의미 |
|---|---|
| `completed` | Guardrail 검증과 MCP 조회가 완료됨 |
| `clarification_required` | 실행 전에 질문을 더 명확히 해야 함 |
| `rejected` | 입력, Metadata, QueryPlan 또는 SQL이 정책 검증에서 거부됨 |
| `failed` | LLM Provider 또는 MCP 실행 등 외부 의존성 문제로 완료하지 못함 |

LLM 설정이 없거나 유효하지 않으면 서버는 기동될 수 있지만 질문 요청은
`failed`/`llm_unavailable`로 응답합니다. Provider의 일시적인 Rate Limit도 같은 공개
코드를 사용하며, 잠시 후 다시 시도할 수 있습니다. 자세한 요청·응답 형식은
[자연어 질문 API 계약](docs/contracts/natural-language-query.md)을 참고합니다.

### 5. 종료

FastAPI 터미널에서 `Ctrl+C`를 눌러 MCP Session과 하위 프로세스를 함께 종료합니다.
일상적인 개발 종료 시 SQL Server 데이터는 유지한 채 컨테이너만 중지합니다.

```bash
docker compose stop
```

`docker compose down -v`는 복원한 데이터베이스가 저장된 Volume까지 삭제하므로
데이터 초기화가 목적일 때만 사용합니다.

## 절대 설계 원칙

1. **Security before Intelligence**
   LLM의 영리함보다 Backend의 정책 통제가 먼저입니다.

2. **Metadata before Intelligence**
   LLM은 Raw Enterprise Database를 직접 해석하지 않고 승인된 Metadata만 사용합니다.

3. **Policy before SQL**
   SQL 생성과 실행 전에 사용자 ACL과 테이블·컬럼 정책을 평가합니다.

4. **Read-Only by Default**
   대상 DB 계정에는 업무 데이터 수정·삭제 권한을 부여하지 않습니다.

5. **Explain Contextually**
   응답에는 실제 사용한 기간, 계산식, 데이터 기준일과 한계를 함께 설명합니다.

6. **Fail Closed, Not Open**
   권한, Metadata, Contract 또는 실행 안전성이 불확실하면 진행하지 않습니다.

## 전체 아키텍처

FastAPI는 Workflow Orchestrator 역할을 담당합니다. LLM이 제안한 QueryPlan과 SQL을 Backend가 검증하고, 대상 DB 접근은 MCP Client Manager와 승인된 MCP Tool을 통해서만 수행합니다.

```text
[Jinja2 Demo Web UI / HTTP API]
   │
   ▼
[Workflow Orchestrator / FastAPI]
   ├── ACL · Metadata · QueryPlan · SQL Guardrail · XAI/Audit
   ├── LLM Provider
   ├── Admin DB
   │
   │ 검증 완료 SQL + 실행 제한
   ▼
[MCP Client Manager / Official MCP SDK]
   │ local stdio
   ▼
[MCP Server / execute_readonly_query]
   │ Read-Only Query Executor
   ▼
[Read-Only MSSQL / AdventureWorks2022]
```

핵심 실행 경계:

* SQL Guardrail은 SQL 구조와 정책을 정적으로 검증합니다.
* MCP Client Manager는 Session, 요청 직렬화와 MCP Call Timeout을 관리합니다.
* MCP Server는 Read-Only 계정, DB Query Timeout과 Maximum Returned Rows를 강제합니다.
* MCP 장애가 발생해도 FastAPI의 직접 DB 실행 경로로 우회하지 않습니다.
* MVP에서는 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 Bounded Result를 Result Handle 없이 LLM에 직접 전달합니다.

상세 구조와 호출 순서는 다음 문서를 따릅니다.

* [전체 아키텍처](docs/architecture/overview.md)
* [컴포넌트 책임과 경계](docs/architecture/component-boundaries.md)
* [질문 처리 시퀀스](docs/architecture/query-execution-sequence.md)
* [프로젝트 모듈 구조](docs/architecture/project-structure.md)

## MVP 방향

3주 MVP는 Docker SQL Server에 복원한 AdventureWorks2022 단일 DB와 하나의 설정된 LLM Provider를 사용합니다. 먼저 자연어 질문부터 Depth 1 조회까지의 Walking Skeleton과 Jinja2 데모 웹 UI를 만들고, 안전 경계와 AWS 배포를 완료한 뒤 `Sales`, `Production`, `Purchasing` 도메인을 조합하는 최대 2-Depth Workflow와 XAI를 검증합니다.

MVP의 범용성은 등록되고 승인된 Metadata의 조합 범위로 제한됩니다. 임의의 Metric, 공식, Join이나 업무 의미를 생성하지 않습니다.

두 역할로 ACL 차이를 검증합니다.

| 역할 | 대표 질문 처리 |
|---|---|
| `supply_risk_analyst` | 판매·재고·공급 데이터를 사용하는 전체 2-Depth 분석 허용 |
| `inventory_viewer` | 판매·구매 Metadata를 노출하지 않고 SQL 생성 전에 거부 |

현재 위치와 완료 조건은 다음 문서를 기준으로 판단합니다.

* [MVP 범위와 Non-Goals](docs/mvp/scope.md)
* [3주 MVP 로드맵](docs/mvp/roadmap.md)
* [Golden Query와 E2E 완료 기준](docs/mvp/acceptance-criteria.md)

## 핵심 Contract

구성요소 사이의 데이터는 명시적인 Contract로 전달합니다.

| Contract | 역할 |
|---|---|
| [RuntimeIntent](docs/contracts/runtime-intent.md) | 자연어 질문을 Metadata 검색 입력으로 구조화 |
| [QueryPlan](docs/contracts/query-plan.md) | 자연어와 SQL 사이의 검증 가능한 실행 계획 |
| [`execute_readonly_query`](docs/contracts/execute-readonly-query.md) | 검증 완료 SQL의 MCP Tool 입출력 |
| [Result Context](docs/contracts/result-context.md) | MVP Direct 전달과 Post-MVP Handle 전달 정책 |
| [XAI Payload](docs/contracts/xai-payload.md) | 최종 설명에 사용할 실제 실행 근거 |

## 중요한 설계 결정

설계 선택의 이유와 버린 대안은 [Architecture Decision Records](docs/adr/README.md)에 기록합니다.

| ADR | 결정 |
|---|---|
| [0001](docs/adr/0001-readonly-db.md) | 대상 DB Read-Only 원칙 |
| [0002](docs/adr/0002-admin-db.md) | 별도 Admin DB 사용 |
| [0003](docs/adr/0003-virtual-fk.md) | 승인된 Virtual FK 관리 |
| [0004](docs/adr/0004-agent-depth.md) | Agent Workflow Depth 제한 |
| [0005](docs/adr/0005-self-healing.md) | Post-MVP Self-Healing 횟수 제한 제안 |
| [0006](docs/adr/0006-result-handle.md) | Post-MVP LLM 배포 모드별 Direct·Handle 결과 전달 전략 |
| [0007](docs/adr/0007-local-stdio-mcp-db-boundary.md) | FastAPI가 관리하는 로컬 stdio MCP 실행 경계 |
| [0008](docs/adr/0008-aws-demo-deployment.md) | 단일 EC2·EBS 기반 AWS 데모 배포 |

## 문서 지도

무엇을 읽어야 할지 헷갈리면 [프로젝트 문서 안내](docs/README.md)에서 시작합니다.

| 궁금한 내용 | 문서 |
|---|---|
| 이 프로젝트가 지키는 방향은 무엇인가? | 현재 README |
| 시스템은 어떻게 연결되는가? | [Architecture 문서](docs/architecture/README.md) |
| 정확한 필드와 오류 형식은 무엇인가? | [Contract 문서](docs/contracts/README.md) |
| 왜 이 설계를 선택했는가? | [ADR 목록](docs/adr/README.md) |
| 지금 어디까지 구현하는가? | [MVP 문서](docs/mvp/README.md) |
| AI와 어떤 방식으로 개발하는가? | [개발 프로토콜](docs/development-protocol.md) |

## AI-Assisted Development 원칙

AI는 구현 보조자, 리뷰어, 테스트 작성자와 대안 제시자 역할을 합니다. 최종 아키텍처 결정과 코드 승인 책임은 개발자에게 있습니다.

Feature는 [Spec과 Plan을 먼저 승인한 뒤 구현하는 개발 절차](docs/features/README.md)를 따릅니다. Claude Code는 Approved Plan 범위의 코드와 테스트를 구현하고 실제 작업·검증 결과를 `tasks.md`에 기록합니다. 구현은 하나의 Feature 범위로 제한하고 이해하고 검증한 코드만 병합합니다. 상세 구현 절차는 [AI-Assisted Development Protocol](docs/development-protocol.md)을 따릅니다.
