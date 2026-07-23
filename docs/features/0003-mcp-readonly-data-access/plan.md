# MCP Read-Only Data Access Plan

* Feature ID: `FEAT-0003`
* Status: `Approved`
* Development Track: `Standard`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)

## 1. 목적과 범위

Approved Spec의 실행 경계를 구현한다: FastAPI가 관리하는 로컬 `stdio` MCP Server(AdventureWorks2022 MSSQL 전용)와 그 Lifecycle을 소유하는 MCP Client Manager, 그 위의 `inspect_schema`·`execute_readonly_query` Tool, `inspect_schema` 결과로 Backend가 구성해 FEAT-0004·FEAT-0005가 사용할 Physical Metadata Catalog. 기존 FEAT-0002 Admin DB Lifespan과 결합하며 FR-001~FR-018·NFR-001~NFR-007을 충족한다.

LLM 호출, 자연어 질문 API, RuntimeIntent·QueryPlan, 실제 사용자 ACL, 전체 SQL AST Guardrail·Plan-SQL Match는 FEAT-0004·FEAT-0006 범위이며 구현하지 않는다. MCP Server는 MSSQL 전용이며 범용 DB Adapter나 Plugin 구조를 만들지 않는다.

**관련 기준**: [ADR 0001](../../adr/0001-readonly-db.md)(Accepted, Read-Only 원칙), [ADR 0007](../../adr/0007-local-stdio-mcp-db-boundary.md)(Accepted, 로컬 stdio 경계와 Week 1 단계적 적용), [컴포넌트 경계](../../architecture/component-boundaries.md), [프로젝트 모듈 구조](../../architecture/project-structure.md)(`app/mcp/{client_manager,lifecycle,contracts}.py`, `app/services/schema_collector.py`, `mcp_server/{server,db,readonly_query_executor}.py`, `mcp_server/tools/*.py` 구조를 그대로 따름), [`inspect_schema`](../../contracts/inspect-schema.md)·[`execute_readonly_query`](../../contracts/execute-readonly-query.md) Contract(둘 다 Accepted). 충돌하는 기준 문서는 없다.

## 2. 핵심 기술 결정

### 대상 DB 연결과 TARGET_DB_* 소유

`mcp_server/`는 MSSQL/AdventureWorks2022 전용이며 범용 Adapter를 두지 않는다. 요청마다 `pyodbc.connect()`를 열고 닫는다(Connection Pool 없음 — 단일 Server·요청 직렬화로 충분). `TargetDBSettings`(`mcp_server/db.py`)가 `TARGET_DB_HOST/PORT/NAME/USER/PASSWORD/DRIVER/ENCRYPT/TRUST_SERVER_CERTIFICATE`를 소유한다(모두 필수, trim 후 빈 값 거부). `SettingsConfigDict(env_file=REPO_ROOT/".env")`로 저장소 루트 `.env`를 읽되 `os.environ`은 전역 변경하지 않으며, 실제 OS 환경변수가 `.env`보다 우선한다. 테스트는 `_env_file=None` 또는 임시 env 파일로 격리한다. FastAPI `Settings`(`app/core/config.py`)에는 `TARGET_DB_*`를 추가하지 않고 FastAPI 서비스 코드는 이 값이나 연결 문자열을 다루지 않는다(FR-017). AWS Secret 주입은 FEAT-0007 범위다.

`mcp_server/server.py`는 `mcp.run()` 전에 `TargetDBSettings` 생성과 연결 자가진단(1회 열고 닫기)을 수행하고, 실패하면 Secret 없이 `stderr`에 기록 후 비정상 종료한다 — Client의 `initialize()` 실패로 관측되어 아래 시작 Timeout에 자연히 포함된다.

Read-Only 최종 경계는 `TARGET_DB_USER`(`data_agent_ro`)의 SELECT-only DB 권한이며, 아래 최소 SQL 검사는 추가 방어다. `ApplicationIntent=ReadOnly`는 연결 의도·Read-Only Routing 설정일 뿐 보안 강제 장치가 아니다. Secret은 로그·예외·Tool 결과에 노출하지 않는다(NFR-007).

### MCP SDK, Tool 실행과 Output Schema

공식 SDK만 사용한다(`mcp.server.fastmcp.FastMCP`, `mcp.client.stdio.stdio_client` + `ClientSession`). 두 Tool은 `async def`로 선언한다 — 설치된 SDK는 동기 함수를 Thread로 넘기지 않고 그대로 호출하므로, 동기 `pyodbc` 작업은 `anyio.to_thread.run_sync()`로 위임한다(별도 Worker Pool 없음). 두 Tool은 반환 타입을 `dict[str, Any]`로 선언하고 `@mcp.tool(structured_output=True)`로 등록해 SDK가 `CallToolResult.structuredContent`를 채우도록 강제한다(bare `dict`는 Output Schema를 만들지 못한다). 서버·클라이언트가 공유하는 별도 Contract 패키지는 만들지 않고 각자 Accepted Contract를 기준으로 독립 구현한다.

### FastAPI Lifespan과 MCP Lifecycle

`app/mcp/lifecycle.py`의 `mcp_lifespan()`은 `MCPClientManager` 하나만 yield한다(Catalog는 다루지 않음). `AsyncExitStack`으로 `stdio_client`+`ClientSession`을 FastAPI Lifespan과 같은 수명으로 유지하고 종료 시 정리한다(단일 프로세스·장기 유지 Session, 요청마다 재시작 없음, FR-002). `asyncio.timeout(30)`으로 `session.initialize()`+`session.list_tools()`를 하나의 범위로 묶고(대상 DB 자가진단 시간 포함), 초과 시 `MCPStartupError(reason="startup_timeout")`. 그 범위 밖에서 `verify_tool_contracts()`가 Tool 이름 2개와 `inputSchema`의 property·required·타입이 Accepted Contract와 정확히 일치하는지 확인한다(하드코딩 비교, 범용 스키마 엔진 없음). 실패하면 `MCPStartupError`.

`app/core/lifespan.py`(FEAT-0002)와의 결합 순서와 실패 처리는 5절을 따른다(중복 서술하지 않음).

### Physical Metadata Catalog

Startup 시 1회 생성한다 — Admin DB·MCP와 같은 Fail Closed 보장, 첫 요청 경합 회피, AdventureWorks 사용자 Schema 규모가 작아 지연이 크지 않음, 매번 새 스냅샷이라 별도 버전 관리가 불필요함이 근거다. Admin DB(SQLite)에는 저장하지 않고 `app/services/schema_collector.py`의 `PhysicalMetadataCatalog`(Pydantic)로 메모리에만 보관해 `app.state.physical_metadata_catalog`에 저장한다. FEAT-0004·FEAT-0005는 이 `app.state` 속성과 `get_table(schema_name, table_name)`을 공개 조회 경계로 사용한다(실제 라우터·Dependency 연결은 각 Feature 책임).

### inspect_schema 구현

`sys.tables`에 `is_ms_shipped=0`으로 시스템 객체를 제외하고 `sys`/`INFORMATION_SCHEMA`/`guest`/`db_*` Role Schema도 제외한다. `sys.columns`+`sys.types`(+`max_length`/`precision`/`scale`)로 MSSQL 선언 형태(`nvarchar(50)`, `nvarchar(max)`, `decimal(19,4)` 등)를 단일 `data_type` 문자열에 담는다(Contract에 새 필드 추가 없음). PK·FK는 `key_ordinal`/`constraint_column_id`로 복합 Key 순서를 보존하고, FK의 Source·Target Table은 항상 `schemas` 결과에도 포함된다. `MS_Description`은 `sys.extended_properties`에서 원문만 수집하고 없으면 `null`이며(FR-006), 번역·요약·Business Metadata 승격은 하지 않는다(FR-008). Schema Inspection Timeout은 15초(MCP Server 내부 고정값, Contract 입력 없음).

### execute_readonly_query 구현

`mcp_server/tools/execute_readonly_query.py`(얇은 진입점)는 `readonly_query_executor.py`(Read-Only Query Executor)에 위임한다. `query_timeout_seconds`(1~15초)·`maximum_returned_rows`(1~500행) 범위 밖은 DB 실행 전에 거부한다. 최소 SQL 검사(대소문자 무시, trailing `;` 제거 후 단어 경계 기준): `SELECT`로 시작하지 않으면 거부, 추가 `;`(다중 Statement) 거부, `--`/`/*`(주석) 거부, `WITH`/`INTO`/`INSERT`/`UPDATE`/`DELETE`/`MERGE`/`EXEC`/`EXECUTE`/`DROP`/`ALTER`/`CREATE`/`TRUNCATE`/`GRANT`/`REVOKE` 거부. 문자열 리터럴로 인한 False Positive는 Week 1 Fail Closed로 허용하며, 실제 Parser는 FEAT-0006 책임이다. 바인딩은 `pyodbc`의 `?` Placeholder만 사용한다. DB 연결 생성용 Connection/Login Timeout은 별도로 두고, 연결 후 `connection.timeout = query_timeout_seconds`로 DB Query Timeout을 적용한 뒤 `cursor.execute()`를 호출한다. `inspect_schema`도 같은 방식으로 `connection.timeout = 15`를 적용하며, Timeout은 구분된 오류로 변환한다. `maximum_returned_rows+1`행을 fetch해 초과분이 있으면 잘라 `truncated=true`(`row_count`는 항상 실제 반환 행 수). JSON 직렬화는 Contract 그대로 NULL→`null`, Decimal→문자열, datetime/date→ISO 8601이다.

### 요청 직렬화, unavailable 상태와 오류 변환

`MCPClientManager`는 `asyncio.Lock()`과 `unavailable` 플래그를 갖는다. Lock 밖 사전 확인(선택적 빠른 실패)은 정확성을 보장하지 않으므로, **Lock 획득 직후 `unavailable`을 반드시 재확인**한 뒤에만 `session.call_tool()`을 호출한다 — 이 재확인이 Race Condition을 막는 지점이다. 같은 Lock 범위 안에서 `asyncio.wait_for(call_tool(...), timeout=20)`을 호출하고, Timeout 또는 `connection_closed`/`subprocess_exited` 같은 재사용 불가능한 Transport 오류가 나면 같은 Lock 범위에서 `unavailable=True`로 전환한다. 이후 모든 호출은 재확인에서 즉시 거부된다. 자동 재연결·MCP Server 재시작은 하지 않으며 `unavailable`은 다음 Lifespan 시작까지 유지된다. Session/Process Pool은 만들지 않는다(FR-013).

`CallToolResult.isError=true`이면 `MCPToolExecutionError`. 성공이면 `structuredContent`만 사용하고(`TextContent` Fallback 파싱 없음), 없거나 Contract Pydantic 검증에 실패하면 `MCPToolExecutionError(reason="invalid_result_contract")`. 원본 Tool/Driver 오류 문자열은 그대로 노출하지 않는다. 예외 3종(`MCPStartupError`/`MCPToolExecutionError`/`MCPTransportError`)은 `reason`으로 세부를 구분하며 `app/mcp/client_manager.py`에만 존재한다 — `mcp_server`는 일반 Python 예외만 발생시킬 뿐 이 타입을 import·생성하지 않는다. `MCPStartupError`는 startup을 막고, 나머지 둘은 요청 처리 중 구조화된 실패로 남으며 어떤 경우에도 대상 DB 직접 실행으로 우회하지 않는다(FR-015, NFR-002).

### Timeout과 입력 상한(확정값)

| 값 | 확정값 |
|---|---|
| MCP Server 시작 Timeout(`initialize`+`list_tools`) | 30초 |
| MCP Call Timeout(Lock 범위 안 `call_tool`) | 20초 |
| Schema Inspection Timeout(MCP Server 내부) | 15초 |
| `query_timeout_seconds` 허용 범위(Tool 입력) | 1~15초 |
| `maximum_returned_rows` 허용 범위(Tool 입력) | 1~500행 |

DB Query Timeout 상한(15초)은 MCP Call Timeout(20초)보다 항상 작게 유지해 DB 자체 Timeout이 먼저 응답할 여지를 남긴다. 실제 운영 `query_timeout_seconds`/`maximum_returned_rows` 값은 FEAT-0004·설정이 이 범위 안에서 결정하며, 표의 값은 상수로 코드에 둔다.

## 3. 구성요소와 파일 책임

| 파일 | 책임 | 변경 |
|---|---|---|
| `app/core/lifespan.py` | Admin DB 준비 뒤 `mcp_lifespan()` 진입, `inspect_schema`+Catalog 구성 결합, 실패 시 정리 후 예외 전파 | 수정 |
| `app/mcp/__init__.py` | 패키지 마커 | 추가 |
| `app/mcp/client_manager.py` | `MCPClientManager`(예외 3종, Lock+`unavailable` 재확인, Timeout, `CallToolResult` 처리) | 추가 |
| `app/mcp/lifecycle.py` | `mcp_lifespan()` — Subprocess/Session 시작·종료, 시작 Timeout, Tool Discovery | 추가 |
| `app/mcp/contracts.py` | `verify_tool_contracts()` — 이름·property·required·타입 비교 | 추가 |
| `app/services/schema_collector.py` | `PhysicalMetadataCatalog` 모델, `build_physical_metadata_catalog()` | 추가 |
| `mcp_server/__init__.py` | 패키지 마커 | 추가 |
| `mcp_server/server.py` | `FastMCP` 인스턴스, Tool 등록(`structured_output=True`), 시작 자가진단, `stdio` 진입점 | 추가 |
| `mcp_server/db.py` | `TargetDBSettings`(`TARGET_DB_*`, `env_file`), 연결 생성·종료 | 추가 |
| `mcp_server/readonly_query_executor.py` | 입력 상한·최소 SQL 검사, Query Timeout, Row 제한·`truncated`, 직렬화 | 추가 |
| `mcp_server/tools/__init__.py` | 패키지 마커 | 추가 |
| `mcp_server/tools/inspect_schema.py` | 시스템 카탈로그 조회 → Contract 구조 | 추가 |
| `mcp_server/tools/execute_readonly_query.py` | `readonly_query_executor.py` 위임 | 추가 |
| `pyproject.toml` / `uv.lock` | `mcp>=1.28,<2`, `pyodbc>=5.3,<6` 의존성, `requires_target_db` pytest marker(`cli` Extra 불요) | Approved Plan 이후 구현 단계 |
| `tests/conftest.py` | Fake MCP Lifespan(Fake `ClientSession`/`MCPClientManager`)·Fake `PhysicalMetadataCatalog` Fixture | 수정 |
| `tests/test_admin_db_lifecycle.py`, `test_app_lifecycle.py`, `test_health.py` | Fake MCP Lifespan Fixture 적용(Docker MSSQL 불요) | 수정 |
| `tests/`(MCP 신규) | 7절 범주에 대응하는 자동 테스트 | 추가 |

`app/core/config.py`, `app/api/`, `docs/architecture/project-structure.md`, `main.py`는 변경하지 않는다. 범용 DI Framework, 범용 Adapter 계층, Connection Pool, 재연결 Manager, 서버·클라이언트 공유 Contract 패키지는 추가하지 않는다.

## 4. 공개 경계

```python
# app/mcp/client_manager.py
class MCPStartupError(RuntimeError):
    reason: str  # "startup_timeout" 포함

class MCPToolExecutionError(RuntimeError):
    reason: str

class MCPTransportError(RuntimeError):
    reason: str  # "call_timeout" | "connection_closed" | "subprocess_exited"

class MCPClientManager:
    """Lock 획득 직후 unavailable을 재확인한 뒤에만 call_tool()을 호출하고,
    structuredContent만 소비한다."""

    def __init__(self, session: ClientSession) -> None: ...
    async def inspect_schema(self, correlation_id: str) -> dict[str, Any]: ...
    async def execute_readonly_query(
        self,
        sql: str,
        parameters: list,
        correlation_id: str,
        query_timeout_seconds: int,
        maximum_returned_rows: int,
    ) -> dict[str, Any]: ...


# app/mcp/lifecycle.py
@asynccontextmanager
async def mcp_lifespan() -> AsyncIterator[MCPClientManager]: ...


# app/mcp/contracts.py
def verify_tool_contracts(tools: list) -> None:
    """이름·property·required·타입이 Accepted Contract와 일치하는지 확인. 실패 시 MCPStartupError."""


# app/services/schema_collector.py — 필드는 inspect_schema Contract를 따름
class PhysicalMetadataCatalog(BaseModel):
    schemas: list[SchemaMetadata]
    foreign_keys: list[ForeignKeyMetadata]

    def get_table(self, schema_name: str, table_name: str) -> TableMetadata | None: ...

def build_physical_metadata_catalog(inspect_schema_result: dict) -> PhysicalMetadataCatalog: ...


# app.state
app.state.mcp_client_manager: MCPClientManager
app.state.physical_metadata_catalog: PhysicalMetadataCatalog


# mcp_server/server.py — Accepted Contract와 1:1 대응하는 Tool Wire Contract
@mcp.tool(structured_output=True)
async def inspect_schema(correlation_id: str) -> dict[str, Any]: ...

@mcp.tool(structured_output=True)
async def execute_readonly_query(
    sql: str,
    parameters: list,
    correlation_id: str,
    query_timeout_seconds: int,
    maximum_returned_rows: int,
) -> dict[str, Any]: ...
```

Private Helper(시스템 카탈로그 SQL, 직렬화 함수 내부 구현 등)는 고정하지 않는다.

## 5. Startup 및 요청 처리 흐름

```text
NOT_STARTED
  → 설정 검증(main.py 임포트) → ASGI startup 진입
  → Admin DB 준비(FEAT-0002, 변경 없음) — 실패 시 startup 미완료
  → mcp_lifespan() 진입: stdio Subprocess 시작(TARGET_DB_* 검증+연결 자가진단)
      → asyncio.timeout(30): session.initialize() → session.list_tools()
      → (범위 밖) verify_tool_contracts()
    실패 시 Session·프로세스 정리(AsyncExitStack) + Admin DB Engine dispose() → 예외 전파 → startup 미완료
  → mcp_client_manager.inspect_schema(...) 1회 호출(Lock 경유) → build_physical_metadata_catalog()
    실패 시 위와 동일하게 정리 후 예외 전파
  → app.state에 admin_db_engine/admin_db_sessionmaker(기존), mcp_client_manager/physical_metadata_catalog(신규) 저장
  → ASGI startup 완료 → 요청 처리
      → Lock 획득 → unavailable 재확인 → call_tool()(Timeout 20초)
      → Timeout/재사용 불가 Transport 오류 시 같은 Lock 범위에서 unavailable=True 전환, 이후 요청은 재확인에서 즉시 거부
  → 종료 신호 → mcp_lifespan() 정리(unavailable 여부 무관) → Admin DB Engine dispose() → STOPPED
```

## 6. 오류와 Fail Closed 처리

Admin DB·MCP 준비, 시작 Timeout, Tool Contract 불일치 실패는 모두 ASGI `startup`을 완료시키지 않는다(5절). 요청 처리 중 실패는 `MCPToolExecutionError`/`MCPTransportError`로 구조화되며 FastAPI는 어떤 경우에도 대상 DB 직접 실행으로 우회하지 않는다(FR-015, NFR-002, ADR-0007 "항상 유지되는 경계"). MCP Server는 `stdout`을 Protocol 전용으로 쓰고 진단은 `stderr`로만 남긴다(FR-014, Secret 제외). 종료 시 `unavailable` 여부와 무관하게 `AsyncExitStack`이 Session·하위 프로세스를 정리한 뒤 Admin DB Engine을 정리한다.

**범위 밖**: 실제 사용자 ACL, RuntimeIntent·QueryPlan 검증, 전체 SQL AST Guardrail·Plan-SQL Match, Workflow Audit 연결, 자동 Session 재연결·MCP Server 재시작(FEAT-0004·FEAT-0006 책임, ADR-0007 Week 2).

## 7. 테스트 및 검증 전략

Acceptance Criteria 각각에 대응하는 개별 테스트를 만들지 않고 핵심 정상·실패 경로가 여러 요구사항을 함께 검증하도록 구성한다. `tests/conftest.py`의 Fake MCP Lifespan/Catalog Fixture로 기존 TestClient 테스트를 Docker MSSQL 없이 유지한다(3절). 실제 Docker AdventureWorks2022가 필요한 항목만 `requires_target_db` marker로 분리한다.

| 범주 | 확인 내용 | 환경 |
|---|---|---|
| 대상 DB 설정 | 필수값 누락·공백 거부, OS 환경변수가 `.env`보다 우선, Secret 비노출(`_env_file` 격리) | 단위 |
| Tool Contract 검증 | 이름·property·required·타입 불일치 시 `MCPStartupError` | 단위 |
| 시작 Timeout | Fake Session으로 무응답 유도, 짧은 Timeout monkeypatch로 `startup_timeout` 확인 | 단위(Fake) |
| Tool Output Schema | `dict[str, Any]`+`structured_output=True` 등록이 실패하지 않음 | 단위 |
| Read-Only Query Executor | SELECT-only·다중 Statement·주석·CTE·`INTO` 거부, 입력 상한 범위 밖 거부, `connection.timeout` 적용, 직렬화 규칙, Timeout 오류 변환(Fake DB) | 단위(Fake) |
| Physical Metadata Catalog | `build_physical_metadata_catalog()` 구성·`get_table()`, Business Metadata 미생성 | 단위 |
| CallToolResult 처리 | `isError`/`structuredContent` 누락·Contract 불일치 각각의 변환 | 단위(Fake) |
| 직렬화·Race Condition | 동시 호출 A/B: A Timeout 중 `unavailable` 전환, B가 재확인 후 거부됨(`connection_closed`/`subprocess_exited` 포함) | 단위(Fake) |
| Schema Inspection | 실제 Schema·Table·Column·타입·PK·FK·`MS_Description`, 시스템 객체 제외 | 실제 DB |
| 정상 SELECT·행 제한 | 바인딩 Parameter, `row_count`/`truncated` | 실제 DB |
| `data_agent_ro` 쓰기 거부 | `UPDATE Production.Product SET Name = Name WHERE 1 = 0`(부작용 없음) 권한 오류 확인 | 실제 DB |
| MCP Lifecycle Smoke Test | `app.state` 채워짐, 종료 시 하위 프로세스 정리 | 실제 DB |

**수동 검증**: `TARGET_DB_PASSWORD`를 틀리게 설정해 기동 시도 후 `stderr`에 원문이 없는지 확인(자동화하기 어려운 항목만).

## 8. 요구사항 추적

| 요구사항 | 설계 | 검증 |
|---|---|---|
| `FR-001` | FastAPI는 MCP Tool을 통해서만 접근 | 코드 리뷰 |
| `FR-002` | `mcp_lifespan()`이 단일 프로세스·단일 Session을 재사용 | MCP Lifecycle Smoke Test |
| `FR-003` | 공식 MCP SDK Client/Server만 사용 | 코드 리뷰 |
| `FR-004` | `asyncio.timeout(30)` 범위의 `initialize`→`list_tools`, 이후 `verify_tool_contracts` | Tool Contract 검증, 시작 Timeout |
| `FR-005` | `sys.tables`(`is_ms_shipped=0`) 기반 수집, 시스템 객체 제외 | Schema Inspection |
| `FR-006` | Column(MSSQL 선언 타입)·PK·FK·`MS_Description`(없으면 `null`) 수집 | Schema Inspection |
| `FR-007` | `inspect_schema` 후 Catalog를 즉시 구성해 `app.state`에 저장 | MCP Lifecycle Smoke Test |
| `FR-008` | `MS_Description` 원문만 수집, Business Metadata 승격 코드 없음 | Physical Metadata Catalog, Schema Inspection |
| `FR-009` | `execute_readonly_query`가 단일 SELECT만 실행 | Read-Only Query Executor, 정상 SELECT |
| `FR-010` | Tool 함수 시그니처가 Contract 입력만 받도록 구성 | 코드 리뷰 |
| `FR-011` | 최소 SELECT-only·단일 Statement·주석·CTE·`INTO` 재검증 | Read-Only Query Executor |
| `FR-012` | 입력 상한 검증, Query Timeout, `+1` fetch로 `truncated` 판별 | Read-Only Query Executor, 정상 SELECT |
| `FR-013` | `asyncio.Lock` 직렬화와 Lock 내부 재확인 | 직렬화·Race Condition |
| `FR-014` | `mcp.run(transport="stdio")` + 진단은 `stderr` | 코드 리뷰 |
| `FR-015` | 예외 변환, Fallback 없음, `mcp_server`는 Backend 타입 미생성 | CallToolResult 처리, 코드 리뷰 |
| `FR-016` | `AsyncExitStack.aclose()`로 정리, `unavailable`과 무관 | MCP Lifecycle Smoke Test |
| `FR-017` | `mcp_server/db.py`가 `TARGET_DB_*`·`.env` 소유, FastAPI 미접근 | 대상 DB 설정, 코드 리뷰 |
| `FR-018` | 필수값·연결 자가진단 실패가 MCP 시작 실패로 합류 | 대상 DB 설정, MCP Lifecycle Smoke Test |
| `NFR-001` | DB 계정 SELECT-only 권한이 실제 경계, 최소 SQL 재검증은 추가 방어 | `data_agent_ro` 쓰기 거부 |
| `NFR-002` | MCP Call Timeout(`unavailable`)과 DB Query Timeout(Tool 오류) 구분 | 직렬화·Race Condition, Read-Only Query Executor |
| `NFR-003` | 단일 프로세스·단일 Session, Pool 미구현 | 코드 리뷰 |
| `NFR-004` | 로컬 `stdio`만 사용, 원격 Transport 코드 없음 | 코드 리뷰 |
| `NFR-005` | 자연어·RuntimeIntent·QueryPlan·LLM·ACL·AST Guardrail 코드 없음 | 코드 리뷰 |
| `NFR-006` | MCP Server는 내부 하위 프로세스로만 존재, 공개 API 없음 | 코드 리뷰 |
| `NFR-007` | `.env`/OS 환경변수만 사용, Secret 미노출 | 대상 DB 설정, 수동 검증 |

Spec Acceptance Criteria는 위 각 행의 설계·검증으로 충족되며 별도 표로 반복하지 않는다.

## 9. 검토 기록과 승인 상태

**미결정 사항**: 없음. 모든 기술 결정은 2절에서 확정했다.

Codex 검토 결과와 사용자 결정을 기록한다. 기존 검토 의견과 이번 재검토 의견은 Plan에 반영되었고 사용자가 Plan을 승인했다.

| Reviewer | 발견 → 결정 | 상태 |
|---|---|---|
| Codex | 설치된 SDK는 동기 Tool을 Thread로 넘기지 않음 → 두 Tool을 `async def` + `anyio.to_thread.run_sync()`로 변경, Worker Pool 미추가 | Resolved |
| Codex | Timeout·상한 미확정, Timeout 이후 Session 상태 불명확 → 값 확정(2절 표), Timeout/재사용 불가 오류 시 `unavailable` 전환 | Resolved |
| Codex | `CallToolResult` 처리와 bare `dict` 반환으로 Output Schema 미생성 위험 → `dict[str, Any]`+`structured_output=True`, `structuredContent`만 소비, `TextContent` Fallback 없음 | Resolved |
| Codex | `TARGET_DB_*`가 환경변수 상속만으로 설명돼 `.env` 격리·자격 증명 경계가 불명확 → `SettingsConfigDict.env_file`, `os.environ` 미변경, 테스트는 `_env_file` 격리 | Resolved |
| Codex | `ApplicationIntent=ReadOnly`를 보안 계층으로 오서술 → SELECT-only DB 권한이 실제 경계, `ApplicationIntent`는 연결 의도일 뿐이라고 정정 | Resolved |
| Codex | 최소 SQL 검사가 CTE·주석·`SELECT INTO`를 다루지 않음 → 단어 경계 검사에 추가, False Positive는 Week 1 Fail Closed로 허용 | Resolved |
| Codex | 구현 후 기존 TestClient 테스트가 Docker MSSQL을 요구하게 됨 → `conftest.py`에 Fake MCP Lifespan/Catalog Fixture 추가 | Resolved |
| Codex | Schema Inspection이 `is_ms_shipped`·타입 정밀도를 보존하지 않을 위험 → 필터 명시, MSSQL 선언 타입 형태 보존 | Resolved |
| Codex | `mcp_lifespan()`의 반환 타입이 본문과 공개 경계에서 서로 다르게 서술됨 → `MCPClientManager`만 yield하는 것으로 통일 | Resolved |
| Codex | 시작 Timeout 적용 범위와 `mcp_server`의 예외 책임이 불명확 → `asyncio.timeout(30)`이 `initialize`+`list_tools`만 감싸고, `mcp_server`는 Backend 예외 타입을 생성하지 않는다고 명확화 | Resolved |
| Codex | DB Query Timeout을 Connection/Login Timeout에 적용하는 표현 → 연결 후 `connection.timeout`에 설정하도록 정정하고 테스트 대상에 포함 | Resolved |
| Codex | 확인한 MCP SDK 1.x 동작에 의존하면서 버전이 미제한되고 CLI Extra가 불필요함 → `mcp>=1.28,<2`로 제한하고 CLI Extra 제거 | Resolved |

## Plan 승인 조건

* [x] Source Spec에 Development Track이 있으면 해당 Track의 문서화 수준을 적용함
* [x] Approved Spec의 모든 요구사항을 추적함
* [x] ADR, Architecture와 Contract에 충돌하지 않음
* [x] 공개 경계, 실패 동작과 테스트 전략이 명확함
* [x] 추가 설계 결정 없이 구현을 시작할 수 있도록 변경 파일과 책임이 명확함
* [x] 기술 미결정 사항이 없음
* [x] 필수 Codex 검토 의견이 해결되거나 기각 근거가 기록됨
