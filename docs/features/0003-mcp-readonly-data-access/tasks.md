# MCP Read-Only Data Access Tasks

* Feature ID: `FEAT-0003`
* Status: `Verified`
* Development Track: `Standard`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)
* Source Plan: [`./plan.md`](./plan.md) (`Approved`)

## 구현 요약

Approved Plan대로 FastAPI가 소유하는 로컬 `stdio` MCP Server(AdventureWorks2022 MSSQL 전용)와 그 Lifecycle을 관리하는 `MCPClientManager`, `inspect_schema`·`execute_readonly_query` Tool, Startup 시 1회 구성해 `app.state`에 저장하는 `PhysicalMetadataCatalog`를 구현했다. FastAPI는 어떤 코드 경로에서도 `TARGET_DB_*`나 대상 DB 연결 문자열을 다루지 않으며, `mcp_server/`만 이를 소유한다. 기존 FEAT-0002 Admin DB Lifespan 뒤에 MCP Lifecycle을 결합했고, 실패 시 이미 연 자원을 정리한 뒤 ASGI `startup`을 완료하지 않는다(Fail Closed).

실제 Docker AdventureWorks2022로 Schema Inspection, 행 제한, `data_agent_ro` 쓰기 거부, Parameter Binding, `connection.timeout` 실제 적용, MCP Lifecycle 전체 흐름(Fake 없는 실제 `main_app` Startup 포함)을 검증했다. 이 과정에서 Plan에 없던 실제 버그 하나(`sys.types` 권한 문제)를 발견해 수정했다(아래 "구현 중 발견 사항" 참고).

**1차 Codex 구현 검토**에서 5건의 발견 사항(실제 MCP Transport 종료 처리 불완전, 원본 Driver·Tool 오류 문자열 노출, 부모 프로세스 환경변수 미상속, Foreign Key Grouping Key 충돌 가능성, 후행 세미콜론 다중 검사 우회)이 나와 모두 수정하고 회귀 테스트를 추가했다. 자세한 내용은 아래 "Codex 구현 검토 발견 사항과 수정(1차)" 절을 참고한다.

**2차 Codex 재검토**에서 1차 수정 4건(Transport 종료 처리, 부모 환경변수 상속, FK Grouping, 후행 세미콜론)은 Resolved로 확인됐고, 1차 발견 5(원본 Driver·Tool 오류 문자열 노출)는 주요 경로는 해결됐지만 `fetchmany()` 경로와 `CONNECTION_CLOSED`가 아닌 `McpError`, Timeout의 `reason` 구분이 남아있다는 추가 발견 2건이 나왔다(mid-call 프로세스 종료 테스트가 Command Line Pattern으로 시스템 전체 프로세스를 찾아 종료할 위험도 별도로 지적됨). 두 건 모두 수정하고 회귀 테스트를 추가했다. 자세한 내용은 아래 "Codex 구현 검토 발견 사항과 수정(2차)" 절을 참고한다.

**3차 Codex 재검토**에서 2차 수정 2건(정확한 자식 프로세스 종료, `fetchmany`/`McpError`/Timeout `reason` 오류 경계)은 Resolved로 확인됐고, `mcp_server/tools/inspect_schema.py`의 `_inspect_schema_sync()`에서 `connection.timeout` 설정과 `connection.cursor()` 호출이 여전히 `pyodbc.Error` 처리 범위 밖에 있다는 발견 1건이 나왔다(2차 완료 보고의 "남은 위험"에도 이미 이 가능성을 기록해 뒀던 부분이다). 수정하고 회귀 테스트를 추가했으며 Codex 재검토에서 Resolved로 확인했다. 자세한 내용은 아래 "Codex 구현 검토 발견 사항과 수정(3차)" 절을 참고한다.

## 요구사항 Coverage

| Spec 요구사항 | Plan 절 | 실제 구현 Task | 검증 결과 |
|---|---|---|---|
| `FR-001` | 2절 | `TASK-004` | 통과(코드 리뷰 — `app/core/config.py`에 `TARGET_DB_*` 없음) |
| `FR-002` | 2절 | `TASK-007` | 통과(MCP Lifecycle Smoke Test) |
| `FR-003` | 2절 | `TASK-004`, `TASK-007` | 통과(코드 리뷰 — 공식 SDK만 import) |
| `FR-004` | 2절 | `TASK-006`, `TASK-007` | 통과(시작 Timeout·Tool Contract 검증 단위 테스트) |
| `FR-005` | 2절 | `TASK-003` | 통과(Schema Inspection, 실제 DB) |
| `FR-006` | 2절 | `TASK-003` | 통과(Schema Inspection, 실제 DB — `MS_Description` 76건 확인) |
| `FR-007` | 2절 | `TASK-008`, `TASK-009` | 통과(app.state 채워짐, Fake+실제 DB 둘 다) |
| `FR-008` | 2절 | `TASK-003`, `TASK-008` | 통과(실제 DB `MS_Description` 원문 확인, Business Metadata 승격 코드 없음) |
| `FR-009` | 2절 | `TASK-002` | 통과(Read-Only Query Executor, 정상 SELECT) |
| `FR-010` | 2절 | `TASK-004` | 통과(코드 리뷰 — Tool 시그니처가 Contract 입력만 받음) |
| `FR-011` | 2절 | `TASK-002` | 통과(Read-Only Query Executor 31개 단위 테스트) |
| `FR-012` | 2절 | `TASK-002` | 통과(Read-Only Query Executor, 실제 DB 행 제한·`truncated`) |
| `FR-013` | 2절 | `TASK-005` | 통과(동시 호출 A/B Lock 재확인 테스트) |
| `FR-014` | 2절 | `TASK-004` | 통과(코드 리뷰 + 수동 검증 — 오류 `stderr`만 사용, `stdout`/`stderr` 모두 Secret 없음) |
| `FR-015` | 2절 | `TASK-005` | 통과(`CallToolResult` 처리 단위 테스트) |
| `FR-016` | 2절 | `TASK-007` | 통과(MCP Lifecycle Smoke Test — `AsyncExitStack` 정리) |
| `FR-017` | 2절 | `TASK-001` | 통과(코드 리뷰 — `mcp_server/db.py`만 `TARGET_DB_*` 소유) |
| `FR-018` | 2절 | `TASK-001`, `TASK-004` | 통과(대상 DB 설정 단위 테스트, MCP Lifecycle Smoke Test) |
| `NFR-001` | 2절 | `TASK-002` | 통과(`data_agent_ro` 쓰기 거부, 실제 DB) |
| `NFR-002` | 2절 | `TASK-002`, `TASK-005` | 통과(Query Timeout이 `connection.timeout`으로 실제 적용됨을 실제 DB로 확인, Call Timeout/Race Condition 단위 테스트) |
| `NFR-003` | 2절 | `TASK-007` | 통과(코드 리뷰 — 단일 Session, Pool 없음) |
| `NFR-004` | 2절 | `TASK-004`, `TASK-007` | 통과(코드 리뷰 — `stdio`만 사용) |
| `NFR-005` | 2절 | 전체 | 통과(코드 리뷰 — 자연어·RuntimeIntent·LLM·ACL·AST Guardrail 코드 없음) |
| `NFR-006` | 2절 | `TASK-004` | 통과(코드 리뷰 — `app/api/` 미변경, 공개 Route 없음) |
| `NFR-007` | 2절 | `TASK-001`, `TASK-004` | 통과(대상 DB 설정 단위 테스트 + 수동 검증 — 오답 비밀번호로 기동 시도해 `stderr`/`stdout`에 원문 없음 확인) |

## `TASK-001` 대상 DB 연결 계층

* Status: `Completed`
* 요구사항: `FR-017`, `FR-018`, `NFR-007`
* 실제 변경 파일:
  * `mcp_server/__init__.py`
  * `mcp_server/db.py`

구현 결과:

* `TargetDBSettings(BaseSettings)`가 `SettingsConfigDict(env_prefix="TARGET_DB_", env_file=REPO_ROOT/".env", extra="ignore")`로 `host/port/name/user/password/driver/encrypt/trust_server_certificate` 8개 필드를 모두 필수로 소유하고, `field_validator`로 trim 후 빈 값을 거부한다. `os.environ`은 전역 변경하지 않으며, 실제 OS 환경변수가 `.env`보다 우선한다(pydantic-settings 기본 우선순위).
* `get_connection()`이 매 호출마다 새 `pyodbc.connect()`를 열고, 연결 실패는 원본 Driver 예외 문자열(Connection String을 포함할 수 있음)을 그대로 노출하지 않고 `ConnectionError("Failed to connect to target database")`로 치환해 던진다.
* `verify_connection()`이 `mcp_server/server.py`의 시작 자가진단에서 사용하는 1회 열고 닫기 확인 함수다.
* `is_timeout_error(exc)`가 SQLSTATE(`HYT00`/`HYT01`)와 메시지 문자열로 Timeout을 식별해 Query Timeout과 다른 DB 오류를 구분하는 데 사용된다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_mcp_server_db.py -q`
* 결과: 통과 (13 passed) — env 로딩, 8개 필드 각각의 공백 거부(매개변수화), Connection String 조립(더미 값), Timeout 오류 식별 3가지.
* 실행 명령(`requires_target_db`): `uv run pytest -m requires_target_db tests/test_mcp_real_target_db.py -q`
* 결과: 통과 — 실제 Docker MSSQL로 `verify_connection()` 성공 확인(수동), `data_agent_ro` 계정으로 실제 연결.
* 수동 검증: `TARGET_DB_PASSWORD`를 임시로 틀린 값으로 바꿔 `db.verify_connection()`과 `python -m mcp_server.server` 둘 다 실행 → 둘 다 실패하고 예외/`stderr` 메시지에 오답 비밀번호 원문이 없음을 직접 문자열 포함 검사로 확인(결과 출력에 비밀번호 값을 남기지 않았다).

Plan과의 차이:

* Connection 생성 Timeout(`CONNECT_TIMEOUT_SECONDS = 5`)은 Plan이 고정하지 않은 Private Helper 상수다. `mcp_tutorial/db.py`에서 검증된 값을 그대로 사용했다.

Reviewer 의견과 처리:

* 미검토

## `TASK-002` Read-Only Query Executor와 `execute_readonly_query` Tool

* Status: `Completed`
* 요구사항: `FR-009`, `FR-010`, `FR-011`, `FR-012`, `NFR-001`, `NFR-002`(DB Query Timeout 부분)
* 실제 변경 파일:
  * `mcp_server/readonly_query_executor.py`
  * `mcp_server/tools/__init__.py`
  * `mcp_server/tools/execute_readonly_query.py`

구현 결과:

* `_validate_input()`이 `query_timeout_seconds`(1~15초)와 `maximum_returned_rows`(1~500행) 범위 밖을 DB 실행 전에 `ValueError`로 거부한다.
* `_validate_sql()`이 대소문자 무시·후행 세미콜론 하나 제거 후 단어 경계 기준으로 `SELECT` 시작 강제, 다중 Statement(`;`) 거부, 주석(`--`/`/*`) 거부, `WITH`/`INTO`/`INSERT`/`UPDATE`/`DELETE`/`MERGE`/`EXEC`/`EXECUTE`/`DROP`/`ALTER`/`CREATE`/`TRUNCATE`/`GRANT`/`REVOKE` 거부를 구현했다(Plan 2절과 동일 키워드 목록).
* `execute()`가 `db.get_connection()`으로 연결을 연 뒤 `connection.timeout = query_timeout_seconds`를 설정하고(연결 생성용 Timeout과 분리) `cursor.execute(sql, list(parameters or []))`로 `?` Placeholder Binding만 사용한다. `maximum_returned_rows + 1`행을 `fetchmany`해 초과분이 있으면 `truncated=true`로 자르고(`row_count`는 항상 실제 반환 행 수), `_serialize_value()`가 `None`→`null`, `bytes`→hex 문자열, `Decimal`→문자열, `datetime`/`date`→ISO 8601로 변환한다.
* `connection.timeout` 설정·`connection.cursor()`·`cursor.execute()`·`cursor.description` 접근·`cursor.fetchmany()`를 모두 하나의 `try: ... except pyodbc.Error as exc:` 경계 안에 둔다(2차 Codex 재검토 수정 사항 — 원래는 `cursor.execute()`만 감싸고 `fetchmany()`는 밖에 있어 그 단계의 실패는 정제되지 않은 원본 `pyodbc.Error`가 그대로 `anyio.to_thread.run_sync()`를 거쳐 FastMCP까지 전달될 수 있었다. 아래 "Codex 구현 검토 발견 사항과 수정(2차)" 참고). Query Timeout은 `db.is_timeout_error()`로 식별해 `TimeoutError`로, 그 외 DB 오류는 `RuntimeError("DB query execution failed")`로 변환한다(원본 `pyodbc` 예외 문자열은 `str(exc)`로 메시지에 포함하지 않는다 — 1차 Codex 검토 수정 사항).
* `mcp_server/tools/execute_readonly_query.py`는 `anyio.to_thread.run_sync()`로 `readonly_query_executor.execute()`를 Thread로 위임하는 얇은 진입점이며, `correlation_id`를 결과에 추가해 반환한다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_mcp_readonly_query_executor.py -q`
* 결과: 통과 (39 passed) — SQL 검사(정상/금지 키워드 9종/CTE/다중 Statement/주석 2종/공백/후행 세미콜론 다중 4종), 입력 상한 경계값(정상 3종·범위 밖 6종), 직렬화(`None`/`Decimal`/`datetime`/`date`/`bytes`/기본 타입), Secret-like Marker를 담은 Fake `pyodbc.Error`가 `cursor.execute()` 실패와 `cursor.fetchmany()` 실패 각각에서 `RuntimeError`/`TimeoutError` 메시지에 남지 않음(2경로 × 2케이스 = 4건).
* 실행 명령(`requires_target_db`): `uv run pytest -m requires_target_db tests/test_mcp_real_target_db.py -q`
* 결과: 통과 — 실제 DB로 행 제한(`truncated=True`, 3행 반환), 제한 이내 미truncated, Parameter Binding(`ProductID = ?`), `data_agent_ro` 계정의 `UPDATE ... WHERE 1 = 0` 거부(SQLSTATE `42000`), `execute()`가 실제 `pyodbc.Connection.timeout`을 7로 설정함을 Connection Proxy로 확인.

Plan과의 차이:

* 없음(SQL 키워드 목록, Timeout·상한 값, 직렬화 규칙 모두 Plan 2절과 동일하게 구현). 1차 Codex 검토로 두 가지를 수정했다(세미콜론 검사 버그, Driver 오류 문자열 비노출). 2차 Codex 재검토로 `fetchmany()`까지 포함하도록 오류 처리 경계를 넓혔다 — 아래 "Codex 구현 검토 발견 사항과 수정(2차)" 참고.

Reviewer 의견과 처리:

* 미검토

## `TASK-003` `inspect_schema` Tool과 시스템 카탈로그 수집

* Status: `Completed`
* 요구사항: `FR-005`, `FR-006`, `FR-008`
* 실제 변경 파일:
  * `mcp_server/tools/inspect_schema.py`

구현 결과:

* `sys.tables`에 `is_ms_shipped = 0` 필터와 `sys`/`INFORMATION_SCHEMA`/`guest`/`db_*` Schema 명시적 제외(`NOT LIKE 'db\_%' ESCAPE '\'`)를 적용해 시스템 객체를 뺀 사용자 정의 Table만 수집한다.
* Column은 `sys.columns`+`sys.types`로 `max_length`/`precision`/`scale`을 반영한 MSSQL 선언 형태 문자열(`nvarchar(50)`, `nvarchar(max)`, `decimal(19,4)`, `datetime2(7)` 등)을 `_format_data_type()`으로 구성한다. `ordinal_position`은 실제 조회된 Column 순서로 1부터 다시 번호를 매긴다(삭제된 Column으로 인한 `column_id` Gap을 Contract의 "1부터 시작" 규칙에 맞춘다).
* PK는 `sys.key_constraints`+`sys.index_columns`로 `key_ordinal` 순서를, FK는 `sys.foreign_keys`+`sys.foreign_key_columns`로 `constraint_column_id` 순서를 보존해 복합 Key를 올바른 순서로 반환한다. FK의 Source/Target Table은 항상 같은 조회의 `schemas` 결과에도 포함된다(Table 필터 조건이 FK 조회에도 동일하게 적용되므로). FK를 조합해 결과 목록으로 묶는 내부 Grouping Key는 `fk.object_id`를 사용한다(반환 Contract의 `foreign_key_name` 필드 자체는 그대로 `fk.name`을 쓴다) — 서로 다른 Schema/Table에 동일한 FK 이름이 존재해도 하나로 합쳐지지 않는다(1차 Codex 검토 수정 사항, 아래 참고).
* `MS_Description`은 `sys.extended_properties`에서 `class = 1`(Object/Column) + `name = 'MS_Description'`만 원문으로 수집하고(`minor_id = 0`은 Table, 그 외는 Column), 번역·요약·자동 생성은 하지 않는다. 없으면 `null`이다.
* Schema Inspection Timeout은 `connection.timeout = 15`로 MCP Server 내부에 고정했다(Contract 입력 아님). `connection.timeout` 설정·`connection.cursor()` 호출·4개 카탈로그 Query의 `execute`/`fetchall`을 모두 하나의 `try: ... except pyodbc.Error as exc:` 경계 안에 둔다(3차 Codex 재검토 수정 사항 — 원래는 `connection.timeout` 설정과 `connection.cursor()` 호출이 그 안쪽 `try` 밖에 있어, 이 두 지점에서 실패하면 원본 Driver 오류가 그대로 `anyio.to_thread.run_sync()`를 거쳐 FastMCP까지 전달될 수 있었다. 아래 "Codex 구현 검토 발견 사항과 수정(3차)" 참고). Timeout은 `TimeoutError("Schema inspection timeout exceeded")`로, 그 외 `pyodbc.Error`는 `RuntimeError("Schema inspection failed")`로 변환하며 `str(exc)`나 원본 Driver 메시지는 포함하지 않는다. SQL·Catalog 구성 로직·반환 구조는 바꾸지 않았다.
* `mcp_server/tools/inspect_schema.py`가 동기 카탈로그 조회 함수(`_inspect_schema_sync`)와 `anyio.to_thread.run_sync()`로 위임하는 비동기 진입점(`inspect_schema`)을 함께 가진다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_mcp_inspect_schema_formatting.py -q`
* 결과: 통과 (17 passed) — `_format_data_type()`의 `nvarchar`/`nvarchar(max)`/`varchar`/`decimal`/`datetime2`/`int`/`bit`/`uniqueidentifier` 등 대표 타입 조합.
* 실행 명령: `uv run pytest tests/test_mcp_inspect_schema_unit.py -q`
* 결과: 통과 (7 passed) — 서로 다른 Schema/Table의 동일 이름 FK가 합쳐지지 않음, 복합 FK Column 순서 보존, Secret-like Marker를 담은 Fake `pyodbc.Error`가 `cursor.execute()` 실패·`connection.timeout` 설정 실패·`connection.cursor()` 호출 실패 세 지점 각각에서 `RuntimeError`/`TimeoutError` 메시지에 남지 않음(3차 재검토로 뒤 두 지점 추가).
* 실행 명령(`requires_target_db`): `uv run pytest -m requires_target_db tests/test_mcp_real_target_db.py -q`
* 결과: 통과 — 실제 AdventureWorks2022로 `schema_count=6`, `table_count=71`, `foreign_keys=90`, `Production.Product`의 PK(`ProductID`)와 Column 확인, 시스템 Schema(`sys`/`INFORMATION_SCHEMA`/`guest`/`db_*`)가 결과에 없음을 확인, `MS_Description` 실제 값 76건 수집 확인(Table 1건 + Column 여러 건 수동 출력으로 원문 확인). 3차 수정 이후에도 회귀 없이 통과.

Plan과의 차이:

* **버그 수정(아래 "구현 중 발견 사항" 참고)**: Column 타입 조회를 `sys.types ON c.user_type_id = ty.user_type_id`에서 `sys.types ON c.system_type_id = ty.system_type_id AND ty.user_type_id = ty.system_type_id`로 변경했다. Plan 2절은 "`sys.columns`+`sys.types`로 MSSQL 선언 형태를 담는다"고만 서술했고 정확한 Join 조건은 Private Helper였으므로, 이 수정은 공개 경계·Contract를 바꾸지 않는 구현 세부 수정이다.
* **버그 수정(1차 Codex 검토)**: FK를 `fk.name`만으로 Grouping하던 것을 `fk.object_id` 기반으로 바꿨다. 아래 "Codex 구현 검토 발견 사항과 수정(1차)" 참고.
* **버그 수정(3차 Codex 재검토)**: `connection.timeout`/`connection.cursor()`를 `pyodbc.Error` 처리 경계 안으로 옮겼다. 아래 "Codex 구현 검토 발견 사항과 수정(3차)" 참고.

Reviewer 의견과 처리:

* 미검토

## `TASK-004` MCP Server 진입점과 시작 자가진단

* Status: `Completed`
* 요구사항: `FR-001`, `FR-003`, `FR-010`, `FR-014`, `FR-018`, `NFR-004`, `NFR-006`, `NFR-007`
* 실제 변경 파일:
  * `mcp_server/server.py`

구현 결과:

* `FastMCP("data-agent-mssql")` 인스턴스에 `inspect_schema`·`execute_readonly_query` 두 Tool을 `@mcp.tool(structured_output=True)`로 등록했다. 두 Tool 함수는 `async def`이고 반환 타입은 `dict[str, Any]`이며, 실제 로직은 `mcp_server/tools/*.py`에 위임하는 얇은 wrapper다.
* `_self_check()`가 `mcp.run()` 호출 전에 `db.verify_connection()`을 실행해 실패하면 `stderr`에만 `타입: 메시지`(Secret 없는 안전한 메시지)를 남기고 `SystemExit(1)`로 비정상 종료한다. `stdout`은 MCP Protocol 전용으로만 쓰인다(수동 검증으로 `stdout`이 비어 있음을 확인).
* `main()`이 `_self_check()` 다음 `mcp.run(transport="stdio")`를 호출하며, `python -m mcp_server.server`로 기동한다.

테스트 또는 검증 결과:

* 수동 검증: `TARGET_DB_PASSWORD`를 오답으로 바꿔 `python -m mcp_server.server`를 실제 하위 프로세스로 실행 → `returncode=1`, `stderr="MCP Server startup self-check failed: ConnectionError: Failed to connect to target database"`, `stdout=""`, 오답 비밀번호 원문이 `stdout`/`stderr` 어디에도 없음을 문자열 포함 검사로 확인.
* 실행 명령(`requires_target_db`, 간접): `uv run pytest -m requires_target_db tests/test_mcp_real_target_db.py -q`의 `test_mcp_lifecycle_smoke_end_to_end`, `test_app_startup_with_real_mcp_populates_state_and_cleans_up_on_shutdown`이 정상 자가진단 경로(연결 성공)를 통해 이 파일을 실행한다.
* 코드 리뷰: `app/core/config.py`, `app/api/`에 `TARGET_DB_*` 또는 MCP 관련 공개 Route가 없음을 확인(`NFR-006`).

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-005` MCP Client Manager

* Status: `Completed`
* 요구사항: `FR-013`, `FR-015`, `NFR-002`
* 실제 변경 파일:
  * `app/mcp/__init__.py`
  * `app/mcp/client_manager.py`

구현 결과:

* `MCPStartupError`/`MCPToolExecutionError`/`MCPTransportError`(모두 `RuntimeError` 하위, `reason: str` 속성) 3종을 이 파일에만 정의했다. `mcp_server/`는 이 타입을 import하거나 생성하지 않는다(코드 리뷰로 확인).
* `MCPClientManager`가 `asyncio.Lock()`과 `_unavailable` 플래그를 갖는다. `_call_tool()`은 Lock 밖에서 먼저 `_unavailable`을 확인해 빠르게 실패하되(선택적 최적화), **Lock을 획득한 직후 반드시 다시 확인**한 뒤에만 `asyncio.wait_for(session.call_tool(...), timeout=20)`을 호출한다 — 이 재확인이 동시 요청의 Race Condition을 막는다.
* `TimeoutError`(20초 초과)가 발생하면 같은 Lock 범위에서 `_unavailable = True`로 전환하고 `reason="call_timeout"`인 `MCPTransportError`를 던진다.
* Transport 단절은 `McpError(error.code == CONNECTION_CLOSED)`, `anyio.BrokenResourceError`, `anyio.ClosedResourceError`, `anyio.EndOfStream`, `OSError`, `EOFError` 여섯 종류를 모두 재사용 불가능한 오류로 취급해 같은 Lock 범위에서 `_unavailable = True`로 전환하고 `reason="connection_closed"`인 `MCPTransportError`를 던진다(1차 Codex 검토 수정 사항 — 원래는 `OSError`/`EOFError`만 잡아 실제 MCP SDK가 Transport 단절 시 던지는 `McpError(CONNECTION_CLOSED)`나 `anyio`의 스트림 예외를 놓쳤다). `CONNECTION_CLOSED`가 아닌 다른 코드의 `McpError`는 Transport 오류로 재해석하지 않지만(`unavailable`을 바꾸지 않음), MCP SDK 내부 예외 타입이나 원본 `message`/`data`를 호출자에게 그대로 노출하지도 않는다 — 고정된 안전 메시지("MCP protocol error")의 `MCPToolExecutionError(reason="tool_protocol_error")`로 변환한다(2차 Codex 재검토 수정 사항 — 원래는 이런 `McpError`를 `raise`로 그대로 다시 던져 SDK 내부 예외 타입이 Backend 공개 경계 밖으로 노출됐다. 아래 "Codex 구현 검토 발견 사항과 수정(2차)" 참고).
* 이후 모든 호출은 재확인에서 즉시 `reason="unavailable"`로 거부되며 자동 재연결은 하지 않는다.
* `CallToolResult.isError=True`이면 `_classify_tool_error()`가 원본 `TextContent`를 그대로 노출하지 않고 `(고정 메시지, reason)` 쌍으로 치환한 뒤 `MCPToolExecutionError`를 던진다. Allowlist는 "timeout" 단어 포함 여부가 아니라 mcp_server가 실제로 만드는 고정 Phrase(`"DB query timeout exceeded"`, `"Schema inspection timeout exceeded"`)의 부분 문자열 포함 여부만 인식하며(FastMCP가 앞에 Tool 실행 오류 Prefix를 붙일 수 있어 부분 일치로 확인), 일치하면 `("MCP tool reported a timeout", "tool_timeout")`, 아니면 `("MCP tool returned an error", "tool_error")`를 반환한다(2차 Codex 재검토 수정 사항 — 원래는 "timeout"이라는 단어의 포함 여부만으로 판정했고 Timeout·일반 오류 둘 다 `reason="tool_error"`라 메시지 문자열을 비교해야만 구분할 수 있었다). 성공이면 `structuredContent`만 사용하고(`TextContent` Fallback 파싱 없음), `structuredContent`가 없거나 Pydantic 검증(`_InspectSchemaToolResult`/`_ExecuteReadonlyQueryToolResult`)에 실패하면 `MCPToolExecutionError(reason="invalid_result_contract")`를 던진다. `_InspectSchemaToolResult`는 `app/services/schema_collector.py`의 `SchemaMetadata`/`ForeignKeyMetadata`를 그대로 재사용해 중복 모델 정의를 피했다.
* `MCPToolExecutionError.reason`은 이제 `"tool_error"`(일반 Tool 오류) / `"tool_timeout"`(DB·Schema Inspection Timeout) / `"tool_protocol_error"`(CONNECTION_CLOSED가 아닌 McpError) / `"invalid_result_contract"` 네 값을 갖는다. 이 네 값 모두 Plan 공개 경계의 `reason: str`(자유 문자열) 범위 안이며 새 예외 클래스나 공개 메서드를 추가하지 않았다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_mcp_client_manager.py -q`
* 결과: 통과 (21 passed) — 두 Tool 성공 경로, `isError` 처리(안전 Phrase Allowlist로 `tool_timeout`/`tool_error` 구분, FastMCP Prefix가 붙어도 부분 일치로 인식, "timeout" 단어만 있고 안전 Phrase가 아니면 `tool_error`로 유지), Secret-like Marker가 `MCPToolExecutionError` 메시지에 남지 않음, `structuredContent` 누락, Contract 검증 실패, Call Timeout 후 `unavailable=True`, `OSError` Transport 오류 후 `unavailable=True`, `McpError(CONNECTION_CLOSED)` 후 `unavailable=True`이고 후속 호출이 `session.call_tool()`을 다시 부르지 않음, `CONNECTION_CLOSED`가 아닌 `McpError`는 `MCPToolExecutionError(reason="tool_protocol_error")`로 변환되고(Marker를 담은 원본 `message`/`data`가 메시지에 없음, `unavailable` 불변) 원본 `McpError`가 호출자에게 노출되지 않음, `anyio.BrokenResourceError`/`ClosedResourceError`/`EndOfStream` 3종 각각이 `unavailable=True`로 전환됨(매개변수화), `unavailable` 상태에서 이후 호출이 세션을 호출하지 않고 즉시 거부됨, 동시 호출 A/B에서 A가 Timeout으로 `unavailable`이 되는 동안 B가 Lock 재확인으로 거부되고 세션이 정확히 1회만 호출됨(`asyncio.gather`로 동시성 재현, `MCP_CALL_TIMEOUT_SECONDS`를 0.05초로 monkeypatch).
* 실행 명령(`requires_target_db`): `test_mcp_real_target_db.py::test_mid_call_subprocess_termination_raises_transport_error_and_marks_unavailable`
* 결과: 통과 — 실제 `mcp_server` 하위 프로세스를 정상 기동한 뒤 대형 `ORDER BY` Cross Join(정렬 대상 약 924만 행)으로 `execute_readonly_query` Tool 호출이 진행되는 도중, `mcp.client.stdio._create_platform_compatible_process`를 감싸 이 테스트가 직접 캡처한 정확한 `anyio.abc.Process` 객체 하나에만 `kill()`을 호출해 그 하위 프로세스를 종료했다(2차 Codex 재검토로 PowerShell `Get-CimInstance`/`CommandLine` 기반 시스템 전체 프로세스 검색을 제거 — 아래 "Codex 구현 검토 발견 사항과 수정(2차)" 참고). 3회 반복 실행 모두 `MCPTransportError(reason="connection_closed")`가 발생했고 원인(`__cause__`)은 실제로 `mcp.shared.exceptions.McpError`("Connection closed")였다. `Process.kill()`은 플랫폼 독립적이라 Windows 전용 skip을 제거했다.

Plan과의 차이:

* `MCPTransportError.reason`을 Plan 공개 경계 주석은 `"call_timeout" | "connection_closed" | "subprocess_exited"` 세 값으로 예시했으나, 실제로는 `"call_timeout"`과 `"connection_closed"` 두 값만 사용한다(`subprocess_exited`를 별도로 구분하지 않고 `connection_closed`로 합친다 — 하위 프로세스 종료도 실제로는 `McpError(CONNECTION_CLOSED)`나 `anyio` 스트림 예외로 관측되므로 자식 프로세스 반환 코드를 별도로 확인하지 않는 한 이 둘을 구분할 근거가 없다). `reason`은 타입 시스템으로 강제되는 열거형이 아니라 자유 문자열이며 Plan 공개 경계 코드 블록도 주석으로만 예시했으므로, Backend 소비자에게 영향 없는 구현 세부 단순화로 판단해 진행했다. 1차 Codex 검토에서 이 단순화 자체는 문제 삼지 않았고, 대신 `(OSError, EOFError)`만으로는 실제 SDK가 던지는 예외를 완전히 잡지 못한다는 점을 지적해 위와 같이 수정했다.
* `MCPToolExecutionError.reason`에 `"tool_timeout"`/`"tool_protocol_error"` 두 값을 새로 추가했다(2차 Codex 재검토 수정). Plan은 `MCPToolExecutionError.reason`의 구체적인 값 목록을 공개 경계에 고정하지 않았으므로(`reason: str`만 명시) 새 값 추가는 Contract·공개 경계 확장이 아니라 그 안에서의 세분화로 판단했다.

Reviewer 의견과 처리:

* 미검토

## `TASK-006` Tool Contract 검증

* Status: `Completed`
* 요구사항: `FR-004`(Contract 검증 부분)
* 실제 변경 파일:
  * `app/mcp/contracts.py`

구현 결과:

* `verify_tool_contracts(tools)`가 `inspect_schema`·`execute_readonly_query` 두 Tool 이름의 존재, `inputSchema.properties` 이름 집합 일치, `required` 집합 일치, 각 필드의 JSON Schema `type` 일치를 하드코딩된 기대값과 비교한다(범용 스키마 엔진 없음). 실패하면 각각 `reason="tool_missing"`/`"tool_contract_mismatch"`인 `MCPStartupError`를 던진다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_mcp_contracts.py -q`
* 결과: 통과 (5 passed) — 정상 일치, Tool 누락, Property 불일치, `required` 불일치, 타입 불일치.

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-007` MCP Lifecycle(`mcp_lifespan()`)

* Status: `Completed`
* 요구사항: `FR-002`, `FR-003`, `FR-004`(시작 Timeout 부분), `FR-016`, `NFR-003`, `NFR-004`
* 실제 변경 파일:
  * `app/mcp/lifecycle.py`

구현 결과:

* `mcp_lifespan()`이 `AsyncExitStack`으로 `stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=REPO_ROOT, env=dict(os.environ)))`와 `ClientSession`을 FastAPI Lifespan과 같은 수명으로 유지한다. `env=dict(os.environ)`로 부모(FastAPI) 프로세스의 OS 환경변수 전체를 자식 MCP Server 프로세스에 명시적으로 전달한다(1차 Codex 검토 수정 사항 — 아래 참고). `os.environ` 자체는 읽기만 하고 변경하지 않는다(`dict(os.environ)`는 스냅샷 복사본).
* `asyncio.timeout(30)`이 `session.initialize()`+`session.list_tools()`를 하나의 범위로 묶고, 초과 시 `MCPStartupError(reason="startup_timeout")`를 던진다. 그 범위 밖에서 `verify_tool_contracts()`를 호출한다. 어느 단계든 실패하면 `AsyncExitStack`이 이미 연 자원을 정리한 뒤 예외가 전파된다(`MCPStartupError`는 그대로 전파, 그 외 예외는 `reason="startup_failed"`로 감싼다).
* `MCPClientManager` 하나만 yield한다(Catalog는 다루지 않는다 — `app/core/lifespan.py` 책임).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_mcp_lifecycle.py -q`
* 결과: 통과 (6 passed) — 정상 성공 시 `stdio`/`Session` Fake의 진입·정리(`__aenter__`/`__aexit__`) 호출 확인, 시작 Timeout(`MCP_STARTUP_TIMEOUT_SECONDS`를 0.05초로 monkeypatch) 시 `reason="startup_timeout"`과 정리 확인, Tool Contract 불일치 시 `reason="tool_missing"`과 정리 확인, 예상 밖 예외가 `reason="startup_failed"`로 감싸짐과 정리 확인, 더미 `TARGET_DB_HOST` OS 환경변수가 실제로 `StdioServerParameters.env`에 전달됨 확인, `mcp_lifespan()` 호출 전후로 `os.environ`이 변경되지 않음 확인.
* 실행 명령(`requires_target_db`): `uv run pytest -m requires_target_db tests/test_mcp_real_target_db.py -q`
* 결과: 통과 — 실제 하위 프로세스로 `mcp_lifespan()` 진입 → 두 Tool 호출(Schema Inspection + SELECT COUNT) → 정상 종료까지 End-to-End 확인(`test_mcp_lifecycle_smoke_end_to_end`). 부모 OS 환경변수가 `.env`보다 우선하는 동작을 실제 자식 프로세스로도 확인했다(`test_real_child_process_prioritizes_os_env_override_over_dotenv` — 존재하지 않는 로그인 이름으로 `TARGET_DB_USER`를 덮어써 자식 프로세스에 전달하면 실제로 그 값이 쓰여 로그인 실패로 빠르게(약 1.3초) 거부됨을 확인. 수정 전 코드로 동일한 실험을 했을 때는 자식이 `.env`의 올바른 `data_agent_ro`로 대체 접속해 오히려 성공했다 — 이 회귀를 실제로 재현한 뒤 수정했다).

Plan과의 차이:

* MCP Server 기동 방식을 `args=[str(server.py 경로)]`(스크립트 직접 실행) 대신 `args=["-m", "mcp_server.server"]` + `cwd=REPO_ROOT`(`StdioServerParameters.cwd`)로 구현했다. 스크립트를 직접 실행하면 `mcp_server` 패키지(특히 `mcp_server.tools` 하위 패키지)의 상대 Import가 `sys.path`에 저장소 루트가 없어 실패한다. `-m` 실행은 Python이 `cwd`를 `sys.path`에 추가하는 표준 동작을 이용해 이 문제를 피한다. 이는 Plan이 고정하지 않은 Private Helper(하위 프로세스 기동 메커니즘) 수준의 결정이며 공개 경계·Contract에 영향이 없다.
* `StdioServerParameters.env`를 원래 지정하지 않았다가(SDK 기본 제한 환경만 사용) 1차 Codex 검토로 `env=dict(os.environ)`을 추가했다. 자세한 내용은 아래 "Codex 구현 검토 발견 사항과 수정" 참고.

Reviewer 의견과 처리:

* 미검토

## `TASK-008` Physical Metadata Catalog

* Status: `Completed`
* 요구사항: `FR-007`, `FR-008`
* 실제 변경 파일:
  * `app/services/__init__.py`
  * `app/services/schema_collector.py`

구현 결과:

* `ColumnMetadata`/`PrimaryKeyMetadata`/`TableMetadata`/`SchemaMetadata`/`ForeignKeyMetadata`/`PhysicalMetadataCatalog`(모두 Pydantic `BaseModel`)를 `inspect_schema` Contract 필드에 맞춰 정의했다. `PhysicalMetadataCatalog.get_table(schema_name, table_name)`이 공개 조회 경계다.
* `build_physical_metadata_catalog(inspect_schema_result)`가 `MCPClientManager.inspect_schema()`가 반환한(이미 Pydantic 검증을 통과한) `dict`에서 `schemas`/`foreign_keys`만 추출해 `PhysicalMetadataCatalog`를 구성한다(`correlation_id`/`summary`는 Tool Wire Contract 전용 필드이므로 Catalog에 포함하지 않는다).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_app_lifespan_mcp_integration.py -q`
* 결과: 통과 (2 passed) — Fake `inspect_schema` 결과로 `app.state.physical_metadata_catalog`가 `PhysicalMetadataCatalog` Instance로 채워지고 `schemas[0].schema_name`이 기대값과 일치.
* 실행 명령(`requires_target_db`): `test_app_startup_with_real_mcp_populates_state_and_cleans_up_on_shutdown`
* 결과: 통과 — 실제 DB 결과로 `catalog.get_table("Production", "Product")`가 `None`이 아님을 확인.

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-009` FastAPI Lifespan 결합

* Status: `Completed`
* 요구사항: `FR-007`, 5절 Startup 흐름, 6절 Fail Closed
* 실제 변경 파일:
  * `app/core/lifespan.py`

구현 결과:

* Admin DB 준비(FEAT-0002, 변경 없음) → `app.state.admin_db_engine`/`admin_db_sessionmaker` 저장 → `async with _mcp_lifespan() as mcp_client_manager:` 진입 → `mcp_client_manager.inspect_schema(correlation_id="startup")` 1회 호출 → `build_physical_metadata_catalog()` → `app.state.mcp_client_manager`/`physical_metadata_catalog` 저장 → `yield` 순서로 구현했다.
* `try: ... finally: engine.dispose()` 하나로 구성해, Admin DB 준비·MCP Startup·`inspect_schema` 중 어디서 실패하든 `finally`에서 Admin DB Engine이 정리된다. `mcp_lifespan()`은 자신의 `AsyncExitStack`으로 실패 시점까지 이미 연 Session·하위 프로세스를 그 자리에서 정리하므로, 예외가 바깥 `finally`에 도달하는 시점에는 MCP 자원이 이미 정리된 뒤다(중첩된 `async with`가 안쪽부터 정리되는 보장을 그대로 이용했다) — MCP 정리가 Admin DB 정리보다 먼저 일어난다는 Plan의 순서를 코드 구조 자체로 만족한다.
* `_mcp_lifespan`을 `from app.mcp.lifecycle import mcp_lifespan as _mcp_lifespan`로 모듈 속성으로 바인딩해, 테스트가 `monkeypatch.setattr("app.core.lifespan._mcp_lifespan", ...)`로 실제 MCP 기동 없이 대체할 수 있게 했다(`TASK-011`).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_app_lifespan_mcp_integration.py -q`
* 결과: 통과 (2 passed) — 정상 Startup 시 `app.state` 채워짐, MCP Startup 실패(`MCPStartupError`를 던지는 Fake)를 주입했을 때 예외가 전파되고 `Engine.dispose()`가 정확히 1회(해당 Admin DB Engine에 대해) 호출됨을 `Engine.dispose` Spy로 확인.
* 실행 명령: `uv run pytest -q`(기존 51개 포함 전체)
* 결과: 통과 (142 passed) — 기존 FEAT-0001/0002 테스트가 MCP 결합 이후에도 깨지지 않음.

Plan과의 차이:

* 1회 `inspect_schema` 호출의 `correlation_id` 값으로 고정 문자열 `"startup"`을 사용했다. Plan은 이 값의 형식을 지정하지 않았고 Audit·Correlation 추적은 FEAT-0006 범위이므로 Private Helper 수준의 결정이다.

Reviewer 의견과 처리:

* 미검토

## `TASK-010` 의존성과 Pytest 설정

* Status: `Completed`
* 요구사항: 구현 인프라(직접 대응하는 FR/NFR 없음)
* 실제 변경 파일:
  * `pyproject.toml`
  * `uv.lock`

구현 결과:

* `uv add "mcp>=1.28,<2" "pyodbc>=5.3,<6"`로 두 의존성을 추가했다(`cli` Extra 미포함, Plan 확정 범위와 정확히 일치). 실제 설치 버전은 `mcp==1.28.1`, `pyodbc==5.3.0`.
* `[tool.pytest.ini_options]`에 `markers = ["requires_target_db: requires a live Docker MSSQL target database (TARGET_DB_*)"]`를 추가했다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q -m requires_target_db`, `uv run pytest -q -m "not requires_target_db"`
* 결과: 각각 통과 — Marker 등록으로 `PytestUnknownMarkWarning` 없이 두 그룹이 정확히 분리됨(8개/134개).

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-011` 기존 테스트를 위한 Fake MCP Lifespan

* Status: `Completed`
* 요구사항: 7절 테스트 전략(기존 테스트가 Docker MSSQL 없이 유지되어야 함)
* 실제 변경 파일:
  * `tests/conftest.py`

구현 결과:

* `FakeMCPClientManager`(`inspect_schema`/`execute_readonly_query`가 고정된 AdventureWorks 유사 결과를 반환)와 이를 yield하는 `fake_mcp_lifespan` Async Context Manager를 추가했다.
* `autouse=True`인 `fake_mcp_lifespan` Fixture가 각 테스트의 `requires_target_db` Marker 여부를 `request.keywords`로 확인해, Marker가 없으면 `monkeypatch.setattr("app.core.lifespan._mcp_lifespan", ...)`로 실제 MCP 기동을 Fake로 대체하고, Marker가 있으면 아무것도 바꾸지 않아 실제 `_mcp_lifespan`(=실제 `mcp_lifespan()`)이 그대로 쓰이게 한다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q -m "not requires_target_db"`
* 결과: 통과 (134 passed) — 기존 FEAT-0001/0002 테스트(`test_health.py`, `test_app_lifecycle.py`, `test_admin_db_lifecycle.py` 등)가 코드 변경 없이 Docker MSSQL 없이도 통과.

Plan과의 차이:

* Plan 3절의 파일 표는 `tests/test_admin_db_lifecycle.py`, `test_app_lifecycle.py`, `test_health.py`를 "수정" 대상으로 명시했으나, 실제로는 이 세 파일을 전혀 수정하지 않고 `tests/conftest.py`의 `autouse` Fixture 하나로 동일한 목표(기존 TestClient 테스트가 Docker MSSQL 없이 동작)를 달성했다. `autouse` Fixture는 `TestClient(main_app)`을 쓰는 모든 현재·향후 테스트에 자동으로 적용되어 파일별 수정보다 누락 위험이 적고, 세 파일의 실제 코드를 건드리지 않아 변경 범위가 더 작다. 이는 테스트 인프라 배선(Wiring) 방식의 차이일 뿐 공개 경계·Contract·요구사항에 영향이 없어 Plan을 수정하지 않고 진행했다(FEAT-0002 TASK-003/TASK-008의 선례와 같은 수준의 구현 세부 결정으로 판단).

Reviewer 의견과 처리:

* 미검토

## `TASK-012` MCP 신규 자동 테스트

* Status: `Completed`
* 요구사항: 7절 테스트 범주 전체
* 실제 변경 파일:
  * `tests/test_mcp_readonly_query_executor.py`(39개, 2차 재검토로 `fetchmany()` 오류 비노출·Timeout 구분 2건 추가)
  * `tests/test_mcp_inspect_schema_formatting.py`(17개)
  * `tests/test_mcp_inspect_schema_unit.py`(7개, 1차 Codex 검토로 신규 추가 — FK Grouping·오류 비노출 Fake 단위 테스트, 3차 재검토로 `connection.timeout`/`connection.cursor()` 오류 비노출 3건 추가)
  * `tests/test_mcp_server_db.py`(13개)
  * `tests/test_mcp_contracts.py`(5개)
  * `tests/test_mcp_client_manager.py`(21개, 2차 재검토로 `tool_timeout`/`tool_protocol_error` reason 구분·Allowlist 정밀화 테스트 추가)
  * `tests/test_mcp_lifecycle.py`(6개)
  * `tests/test_app_lifespan_mcp_integration.py`(2개)
  * `tests/test_mcp_real_target_db.py`(10개, 전부 `requires_target_db`, 2차 재검토로 mid-call 종료 테스트를 정확한 Process 객체 캡처 방식으로 재작성)

구현 결과 및 Plan 7절 범주 대응:

| Plan 7절 범주 | 테스트 파일 | 환경 |
|---|---|---|
| 대상 DB 설정 | `test_mcp_server_db.py` | 단위 |
| Tool Contract 검증 | `test_mcp_contracts.py` | 단위 |
| 시작 Timeout | `test_mcp_lifecycle.py` | 단위(Fake) |
| Tool Output Schema | `mcp_server` 전체 Import 성공 + `TASK-004`의 실제 Tool 호출 결과로 간접 확인(`structuredContent` 채워짐은 `test_mcp_client_manager.py`가 확인) | 단위 |
| Read-Only Query Executor | `test_mcp_readonly_query_executor.py`, `test_mcp_real_target_db.py`(Timeout 적용) | 단위(Fake)+실제 DB |
| Physical Metadata Catalog | `test_app_lifespan_mcp_integration.py` | 단위 |
| CallToolResult 처리 | `test_mcp_client_manager.py` | 단위(Fake) |
| 직렬화·Race Condition | `test_mcp_client_manager.py`(`test_concurrent_calls_recheck_unavailable_inside_lock`) | 단위(Fake) |
| Schema Inspection | `test_mcp_real_target_db.py` | 실제 DB |
| 정상 SELECT·행 제한 | `test_mcp_real_target_db.py` | 실제 DB |
| `data_agent_ro` 쓰기 거부 | `test_mcp_real_target_db.py` | 실제 DB |
| MCP Lifecycle Smoke Test | `test_mcp_real_target_db.py`(`test_mcp_lifecycle_smoke_end_to_end`, `test_app_startup_with_real_mcp_populates_state_and_cleans_up_on_shutdown`) | 실제 DB |

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q`
* 결과: 통과 (172 passed, 1 warning — 기존 `httpx`/`starlette.testclient` Deprecation 경고, 이 Feature와 무관)
* 실행 명령: `uv run pytest -q -m "not requires_target_db"`
* 결과: 통과 (162 passed, 10 deselected)
* 실행 명령: `uv run pytest -q -m requires_target_db`
* 결과: 통과 (10 passed, 162 deselected)

Plan과의 차이:

* "Tool Output Schema" 범주를 `dict[str, Any]`+`structured_output=True` 등록 실패 여부를 확인하는 별도 단위 테스트로 분리하지 않고, 실제 Tool 호출(Fake·실제 DB 둘 다)이 `structuredContent`를 성공적으로 채우는 것으로 간접 검증했다. Import 시점에 `@mcp.tool(structured_output=True)` 데코레이터가 `dict[str, Any]` 반환 타입에 대해 `InvalidSignature`를 던지면 `mcp_server.server` Import 자체가 실패하므로(SDK 동작, `func_metadata.py` 확인), 이 파일이 정상 Import되고 Tool 호출이 `structuredContent`를 반환한다는 사실 자체가 이 범주의 요구를 만족한다고 판단했다.

Reviewer 의견과 처리:

* 미검토

## 구현 중 발견 사항

### `sys.types`가 `data_agent_ro` 권한으로 일부 User-Defined Type을 숨겨 Column이 누락되는 문제

`inspect_schema`를 실제 AdventureWorks2022로 최초 검증하는 중 `Production.Product` Table의 `Name` Column이 결과에서 통째로 빠지는 것을 발견했다. 원인을 조사한 결과:

* AdventureWorks2022는 `Name`, `Flag`, `NameStyle` 등 여러 User-Defined Type(UDT)을 사용하며, `Production.Product.Name` Column은 `dbo.Name`(nvarchar(50) 기반 UDT) 타입이다.
* SQL Server의 Metadata 가시성 보안 때문에 `data_agent_ro` 계정은 `sys.types`에서 이 UDT 행 자체를 볼 수 없다(`SELECT * FROM sys.types WHERE user_type_id = 260`이 0행 반환, `TYPE_NAME(260)`도 `NULL` 반환 — 둘 다 같은 권한 모델을 따른다).
* 원래 Query는 `sys.columns.user_type_id = sys.types.user_type_id`로 INNER JOIN했으므로, 이 UDT Column은 JOIN 대상이 없어 결과에서 조용히 사라졌다(오류 없이 누락).

수정: JOIN 조건을 `c.system_type_id = ty.system_type_id AND ty.user_type_id = ty.system_type_id`로 바꿔, UDT 자체가 아니라 그 기반 시스템 타입(예: `nvarchar`)의 행을 조회하도록 했다. 시스템 기본 타입 행은 권한과 무관하게 항상 보이므로 UDT 여부와 관계없이 모든 Column이 누락 없이 조회된다. 수정 후 `Production.Product`의 25개 Column이 모두 정상 조회됨을 확인했다(`Name` 포함). 이 방식은 UDT의 별칭 이름 대신 실제 물리 저장 타입(`nvarchar(50)`)을 보고하므로, Contract가 정의한 `data_type`의 의미("대상 DB의 Physical 데이터 타입")에도 더 부합한다.

이 문제는 Contract·공개 경계를 바꾸지 않는 순수 구현 버그이므로 사용자에게 별도 승인을 요청하지 않고 직접 수정했다. `data_agent_ro`에 부여된 권한을 바꾸는 대신 Query를 조정해 해결했으므로 DB 계정의 SELECT-only 원칙(ADR-0001)도 그대로 유지된다.

## Codex 구현 검토 발견 사항과 수정(1차)

Codex가 초기 구현을 검토해 발견한 5건이다. 다섯 건 모두 공개 경계·Contract·Plan을 바꾸지 않는 구현 버그 또는 방어 강화이므로 사용자 재승인 없이 직접 수정했다. Codex 재검토는 아직 받지 않았다.

### 발견 1 — 실제 MCP Transport 종료 처리가 불완전함

* 심각도: High — 하위 프로세스가 실제로 죽거나 stdio가 끊겨도 `MCPClientManager`가 이를 감지하지 못하면 `unavailable` 전환이 일어나지 않고, 다음 호출이 죽은 Session에 걸려 예기치 않게 멈추거나 알 수 없는 예외로 새어나갈 수 있었다.
* 원인: `_call_tool()`이 `(OSError, EOFError)`만 잡았다. 실제 MCP Python SDK(`mcp==1.28.1`)는 Transport 단절을 `McpError(error.code == CONNECTION_CLOSED)`, `anyio.BrokenResourceError`, `anyio.ClosedResourceError`, `anyio.EndOfStream`으로도 전달할 수 있는데 이들은 `OSError`/`EOFError`의 하위 클래스가 아니라서 잡히지 않았다.
* 실제 수정 내용: `app/mcp/client_manager.py`의 `_call_tool()`에 `except McpError as exc: if exc.error.code == CONNECTION_CLOSED: ...` 분기와 `except (OSError, EOFError, anyio.BrokenResourceError, anyio.ClosedResourceError, anyio.EndOfStream) as exc:` 분기를 추가했다. 두 분기 모두 같은 Lock 범위에서 `_unavailable = True`로 전환하고 `MCPTransportError(reason="connection_closed")`를 던진다. `CONNECTION_CLOSED`가 아닌 다른 코드의 `McpError`는 새로운 의미를 부여하지 않고 그대로 다시 던진다(`raise`). `subprocess_exited`를 별도 `reason`으로 만들지는 않았다 — Plan 공개 경계 주석의 세 값 중 하나였지만, 실제로 하위 프로세스가 죽는 상황도 `McpError(CONNECTION_CLOSED)`나 `anyio` 스트림 예외로 관측되어(아래 실제 검증 결과 참고) 이를 별도로 구분할 근거(예: 자식 프로세스 반환 코드 확인)를 새로 만들지 않는 한 나눌 수 없기 때문이다. `reason`은 강제되는 열거형이 아닌 자유 문자열이라 이 통합은 Backend 소비자에게 영향이 없다.
* 추가한 회귀 테스트:
  * `tests/test_mcp_client_manager.py`: `test_mcp_error_connection_closed_marks_manager_unavailable_and_stops_calling_session`(Fake `McpError(ErrorData(code=CONNECTION_CLOSED, ...))`), `test_mcp_error_with_other_code_is_not_treated_as_transport_error`(다른 code는 그대로 전파, `unavailable` 불변), `test_anyio_transport_exceptions_mark_manager_unavailable_and_stop_calling_session`(`anyio.BrokenResourceError`/`ClosedResourceError`/`EndOfStream` 3종 매개변수화, 각각 `unavailable=True` 전환과 이후 `session.call_tool()` 미호출 확인).
  * `tests/test_mcp_real_target_db.py::test_mid_call_subprocess_termination_raises_transport_error_and_marks_unavailable`(`requires_target_db`, Windows 전용): 실제 `mcp_server` 하위 프로세스를 정상 기동해 `inspect_schema` 1회 성공시킨 뒤, 정렬을 강제하는 대형 Cross Join(`sys.all_objects` 자기 조인 약 924만 행 + `ORDER BY`)으로 `execute_readonly_query`를 호출하는 동안 별도 PowerShell 프로세스(`Get-CimInstance`로 `mcp_server.server` 명령줄을 가진 `python.exe` 탐색 후 `Stop-Process -Force`)가 그 하위 프로세스를 강제 종료한다. 사용자 지침의 "가능하면 실제 하위 프로세스를 Tool 호출 중 종료" 요구를 그대로 구현했다 — 별도 Test 전용 MCP 서버나 Mock Protocol 구현 없이 실제 `mcp_server/server.py`와 PowerShell 프로세스 종료만으로 재현 가능해 과도한 Test Infrastructure가 필요하지 않았다.
* 검증 결과: 3회 반복 실행 모두 통과(각 4.3~4.6초)했고 매번 `MCPTransportError(reason="connection_closed")`가 발생했다. `__cause__`를 직접 출력해 확인한 결과 실제 원인은 `mcp.shared.exceptions.McpError`("Connection closed")였다 — 이 SDK 버전에서 mid-call 하위 프로세스 종료가 `McpError(CONNECTION_CLOSED)`로 관측됨을 실측으로 확인했다. Fake 기반 회귀 테스트(단위, `requires_target_db` 불필요)와 함께 `uv run pytest -q`에 포함해 실행했다 — 통과.
* 상태: Resolved(2차 Codex 재검토에서 확인). 이 발견을 검증하던 mid-call 종료 테스트 자체가 Command Line Pattern으로 시스템 전체 프로세스를 종료할 위험이 있다는 별도 지적을 받아 "Codex 구현 검토 발견 사항과 수정(2차)" 발견 A에서 다시 수정했다.

### 발견 2 — 원본 Driver·Tool 오류 문자열이 Backend까지 노출될 수 있었음

* 심각도: High — `pyodbc` 예외 메시지에는 드물지 않게 Connection String 조각이나 상세 Driver 정보가 담긴다. 수정 전 코드는 `RuntimeError(f"... : {exc}")` 형태로 `str(exc)`를 그대로 예외 메시지에 넣었고, Client Manager도 `CallToolResult`의 임의 `TextContent`를 그대로 `MCPToolExecutionError` 메시지로 사용했다. 원본 문자열이 안전하다고 단정한 채 구현했으나 실제로 검증하지 않았다.
* 실제 수정 내용:
  * `mcp_server/readonly_query_executor.py`: `raise RuntimeError(f"DB query execution failed: {exc}")` → `raise RuntimeError("DB query execution failed")`(고정 메시지, `str(exc)` 제거).
  * `mcp_server/tools/inspect_schema.py`: `raise RuntimeError(f"Schema inspection failed: {exc}")` → `raise RuntimeError("Schema inspection failed")`(동일).
  * `app/mcp/client_manager.py`: `_extract_error_text()`로 뽑은 원본 텍스트를 그대로 쓰던 것을 `_classify_tool_error_message()`로 바꿨다 — 원본 텍스트는 "timeout" 부분 문자열 포함 여부만 Allowlist로 판정하는 데 쓰고, 실제 예외 메시지는 항상 `"MCP tool reported a timeout"` 또는 `"MCP tool returned an error"` 둘 중 고정된 값이다. 원본 `TextContent`는 어떤 경우에도 Backend 예외 메시지에 등장하지 않는다.
  * Query Timeout/Schema Inspection Timeout 메시지(`TimeoutError(f"DB query timeout exceeded ({query_timeout_seconds}s)")`, `TimeoutError("Schema inspection timeout exceeded")`)는 원래도 우리가 만든 고정 형식이라 수정하지 않았다(설정값만 포함, Driver 원문 없음).
  * 성공 결과는 원래대로 `structuredContent`만 사용하며 `TextContent` JSON Fallback을 만들지 않는다 — 이 부분은 변경하지 않았다.
* 추가한 회귀 테스트:
  * `tests/test_mcp_readonly_query_executor.py::test_execute_does_not_leak_raw_pyodbc_error_text`: Secret-like Marker와 `PWD=hunter2;SERVER=internal-host,1433` 형태의 문자열을 담은 Fake `pyodbc.Error`를 주입해 `RuntimeError` 메시지에 Marker·Driver 상세가 전혀 없음을 확인. `test_execute_still_distinguishes_timeout_from_generic_failure`로 Timeout은 여전히 구분됨을 확인.
  * `tests/test_mcp_inspect_schema_unit.py::test_inspect_schema_does_not_leak_raw_pyodbc_error_text`, `test_inspect_schema_still_distinguishes_timeout_from_generic_failure`: 위와 동일한 패턴을 `_inspect_schema_sync()`에도 적용.
  * `tests/test_mcp_client_manager.py::test_is_error_result_raises_tool_execution_error_with_safe_fixed_message`(기존 `test_is_error_result_raises_tool_execution_error_with_text`를 이 목적에 맞게 개명·수정 — 이제 원문 "boom"과 Marker가 메시지에 없고 고정 문자열과 정확히 일치함을 확인), `test_tool_error_with_timeout_text_is_classified_as_timeout`, `test_tool_error_without_timeout_text_is_classified_as_generic`(Timeout·일반 오류 구분 확인).
* 검증 결과: 위 테스트 전부 통과. 실제 DB 경로(`test_mcp_real_target_db.py`)의 나머지 테스트에서도 예외 메시지에 실제 Secret이 등장하지 않음을 이번 최종 검증의 정적 검색으로 재확인했다(아래 "최종 검증 기록" 참고).
* 상태: 주요 경로(정상 `cursor.execute()` 실패, Tool `isError` 결과의 `TextContent`)는 2차 Codex 재검토에서 Resolved로 확인됐다. 다만 `cursor.fetchmany()` 실패 경로, `CONNECTION_CLOSED`가 아닌 `McpError`의 원본 `message`/`data` 노출, Timeout이 `reason`이 아니라 메시지 문자열로만 구분되는 문제 3가지가 추가로 남아있다는 지적을 받아 "Codex 구현 검토 발견 사항과 수정(2차)" 발견 B에서 마저 수정했다. 이 발견 2는 이제 완전히 Resolved다(2차 수정 포함).

### 발견 3 — 부모 프로세스 환경변수가 자식 MCP Server에 상속되지 않음

* 심각도: Medium — `StdioServerParameters.env`를 지정하지 않으면 MCP SDK가 `get_default_environment()`(제한된 안전 기본값)만 자식에 전달한다. `mcp_server/db.py`는 절대 경로의 `.env` 파일을 직접 읽으므로 정상 배포 시나리오 자체는 동작했지만, "실제 OS 환경변수가 `.env`보다 우선한다"는 설계(Plan 2절, TASK-001)가 부모(FastAPI) 프로세스에서 설정한 OS 환경변수에 대해서는 자식 프로세스에서 성립하지 않았다. TASK-007에는 "하위 프로세스에 OS 환경변수를 상속시킬 필요가 없다"고 잘못 기록되어 있었다(이번에 정정).
* 실제 수정 내용: `app/mcp/lifecycle.py`의 `StdioServerParameters(...)`에 `env=dict(os.environ)`를 추가해 부모 프로세스의 OS 환경변수 전체를 자식에 명시적으로 전달한다. `dict(os.environ)`은 스냅샷 복사본이며 `os.environ` 자체를 변경하지 않는다. 환경변수 값은 어떤 로그·오류에도 출력하지 않는다.
* 추가한 회귀 테스트:
  * `tests/test_mcp_lifecycle.py::test_mcp_lifespan_passes_parent_os_environment_to_child_process`: 더미 `TARGET_DB_HOST` OS 환경변수를 설정하고 `mcp_lifespan()`을 호출해 Fake `stdio_client`가 받은 `StdioServerParameters.env`에 그 값이 실제로 담겨 전달됨을 확인.
  * `tests/test_mcp_lifecycle.py::test_mcp_lifespan_does_not_mutate_os_environ`: 호출 전후로 `os.environ` 전체가 바뀌지 않음을 확인.
  * `tests/test_mcp_real_target_db.py::test_real_child_process_prioritizes_os_env_override_over_dotenv`(`requires_target_db`): 존재하지 않는 로그인 이름(`definitely_not_a_real_login_xyz`)으로 `TARGET_DB_USER` OS 환경변수를 덮어써 실제 `python -m mcp_server.server` 자식 프로세스에 전달했다. 수정 전 코드로 먼저 재현했을 때는 자식이 이 오답 값을 무시하고 `.env`의 올바른 `data_agent_ro`로 대체 접속해 **성공**해버렸다(우선순위 버그를 직접 재현). 수정 후에는 자식이 실제로 그 오답 로그인을 사용해 약 1.3초 만에 로그인 실패로 빠르게 거부되고, `stdout`/`stderr` 어디에도 그 값이 남지 않음을 확인했다.
* 검증 결과: 4개 회귀 테스트 모두 통과. 오답 로그인 이름은 실제 Secret이 아니라 테스트가 만든 더미 문자열이며 결과 어디에도 실제 `TARGET_DB_*` 값은 출력하지 않았다.
* 상태: Resolved(2차 Codex 재검토에서 확인)

### 발견 4 — Foreign Key Grouping Key가 `fk.name`만 사용해 충돌 가능

* 심각도: Medium — MSSQL의 FK 제약 이름은 Schema 범위로 유일하며 DB 전체 유일은 아니다. 서로 다른 Schema/Table에 동일한 이름의 FK가 있으면(가능한 상황) 수정 전 `foreign_keys_map`이 `fk_name`만으로 Grouping해 서로 무관한 두 FK의 Column 목록이 하나로 섞였을 것이다. AdventureWorks2022 실 데이터에는 이런 이름 충돌이 없어 지금까지의 실제 DB 테스트로는 이 결함이 드러나지 않았다.
* 실제 수정 내용: `mcp_server/tools/inspect_schema.py`의 `_FOREIGN_KEY_QUERY`에 `fk.object_id`를 추가하고 `ORDER BY`도 `fk.object_id, fkc.constraint_column_id`로 바꿨다. `foreign_keys_map`/`fk_order`의 Key를 `fk_name` 문자열에서 `fk_object_id`(정수, DB 전체 유일)로 바꿨다. 반환 Contract의 `foreign_key_name` 필드 값 자체는 그대로 `fk.name`을 사용하므로 Wire Contract는 바뀌지 않는다.
* 추가한 회귀 테스트: `tests/test_mcp_inspect_schema_unit.py::test_fk_grouping_does_not_merge_same_name_across_different_tables`(서로 다른 Schema/Table에 같은 이름 `"FK_Same_Name"`을 가진 Fake FK 두 개가 별도 결과로 유지됨을 확인), `test_fk_composite_columns_preserve_constraint_column_order`(복합 FK의 `source_columns`/`target_columns`가 `constraint_column_id` 순서대로 유지됨을 확인).
* 검증 결과: 두 테스트 모두 통과. 실제 DB 재검증(`test_inspect_schema_returns_adventureworks_user_schemas`)에서도 `foreign_keys=90`건으로 수정 전과 동일해(AdventureWorks2022에는 이름 충돌이 없으므로 결과가 달라지지 않는 것이 정상) 회귀가 없음을 확인했다.
* 상태: Resolved(2차 Codex 재검토에서 확인)

### 발견 5 — 후행 세미콜론을 전부 제거해 `SELECT 1;;;`이 통과함

* 심각도: Low — `cleaned.rstrip(";")`가 후행 세미콜론을 모두 제거한 뒤 다중 Statement 여부를 검사했기 때문에, `SELECT 1;;;`처럼 후행 세미콜론이 여러 개인 입력이 세미콜론 하나만 있는 것처럼 통과했다. 실제로 `pyodbc.execute()`가 이런 입력을 어떻게 처리하는지는 Driver 동작에 달려 있어 다중 Statement 우회로 이어질 수 있는 방어 허점이었다(SELECT-only 최종 경계는 `data_agent_ro` 계정 권한이지만, 이 최소 검사도 "추가 방어" 역할을 하므로 방어 허점 자체가 문제였다).
* 실제 수정 내용: `mcp_server/readonly_query_executor.py`의 `_validate_sql()`에서 `cleaned.rstrip(";").rstrip()`을 `if cleaned.endswith(";"): cleaned = cleaned[:-1].rstrip()`로 바꿨다 — 후행 세미콜론을 정확히 하나만 제거하고, 제거 후에도 `;`가 남아 있으면 다중 Statement로 거부한다.
* 추가한 회귀 테스트: `tests/test_mcp_readonly_query_executor.py::test_validate_sql_rejects_multiple_trailing_semicolons`(`"SELECT 1;;"`, `"SELECT 1;;;"`, `"SELECT 1; SELECT 2"`, `"SELECT 1;; SELECT 2"` 4종 매개변수화로 모두 거부됨을 확인). 기존 `test_validate_sql_strips_trailing_semicolon`(`"SELECT 1;"`은 여전히 허용)은 그대로 유지해 정상 케이스가 깨지지 않았음을 함께 확인한다.
* 검증 결과: 5개 테스트 모두 통과.
* 상태: Resolved(2차 Codex 재검토에서 확인)

## Codex 구현 검토 발견 사항과 수정(2차)

2차 Codex 재검토에서 1차 수정 4건(Transport 종료 처리, 부모 환경변수 상속, FK Grouping, 후행 세미콜론)은 Resolved로 확인됐다. 1차 발견 2(원본 Driver·Tool 오류 문자열 노출)의 주요 경로도 Resolved로 확인됐지만, 그 경계가 완전하지 않다는 지적과 함께 1차 수정을 검증하던 테스트 자체의 위험이 새로 발견되어 총 2건을 추가로 수정했다. 둘 다 공개 경계·Contract·Plan을 바꾸지 않는 구현 버그 또는 방어 강화이므로 사용자 재승인 없이 직접 수정했다.

### 발견 A — Mid-call 프로세스 종료 테스트가 Command Line Pattern에 맞는 모든 프로세스를 종료할 위험

* 심각도: High(테스트 안전성) — `tests/test_mcp_real_target_db.py`의 1차 수정 검증 테스트가 `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'mcp_server.server' }`로 시스템 전체 프로세스를 검색해 일치하는 모든 PID에 `Stop-Process -Force`를 실행했다. 같은 시스템에서 사용자가 별도로 실행 중인 MCP Server나, 병렬로 도는 다른 테스트 프로세스까지 이 조건에 우연히 일치하면 함께 종료될 수 있었다.
* 실제 수정 내용: PowerShell·`Get-CimInstance`·Command Line Pattern 검색을 전부 제거했다. 대신 `mcp.client.stdio._create_platform_compatible_process`(MCP SDK가 실제 자식 프로세스를 생성하는 지점)를 감싸 원래 함수를 호출한 뒤 반환된 정확한 `anyio.abc.Process`(Windows에서는 `Process`, 필요 시 SDK의 `FallbackProcess`) 객체 하나만 테스트 지역 변수에 캡처한다. Tool 호출이 진행되는 도중 이 객체 하나에만 `process.kill()`(동기 메서드, PID 검색·이름 매칭 없음)을 호출한다. `mcp_lifespan()`이 성공했다면 캡처가 반드시 일어났어야 하므로, `assert "process" in captured`로 캡처하지 못한 경우 어떤 프로세스도 건드리지 않고 테스트를 즉시 실패시킨다. 테스트 실패·예외 상황에도 `try/finally`로 캡처된 프로세스가 아직 살아있으면(`process.returncode is None`) 정리하도록 했다. `anyio.abc.Process.kill()`은 플랫폼 독립적이라 `@pytest.mark.skipif(sys.platform != "win32", ...)`도 제거했다 — `subprocess_exited`와 `connection_closed`를 별도 `reason`으로 나누지 않는 기존 설계는 그대로 유지한다(사용자 지침대로 이번 수정 범위가 아니다).
* 추가한 회귀 테스트: 기존 `test_mid_call_subprocess_termination_raises_transport_error_and_marks_unavailable`(`requires_target_db`)를 위 방식으로 재작성했다 — 별도 신규 테스트를 추가하지 않고 기존 테스트 자체의 프로세스 식별·종료 방식을 교체했다.
* 검증 결과: 3회 반복 실행 모두 통과(각 2.9~3.9초 — PowerShell 하위 프로세스 기동 오버헤드가 사라져 이전(4.3~4.6초)보다 빨라졌다). 매 실행 뒤 `Get-CimInstance`로 `mcp_server.server` 명령줄을 가진 잔여 `python.exe` 프로세스가 없는지 수동으로 확인했다(0건). `tests/`, `mcp_server/`, `app/` 전체에서 `Get-CimInstance`/`CommandLine`/`Stop-Process`/`powershell` 문자열을 검색해 시스템 전체 프로세스를 찾아 종료하는 코드가 더 이상 없음을 확인했다.
* 상태: Resolved(3차 Codex 재검토에서 확인)

### 발견 B — Tool 오류 변환 경계가 불완전함(`fetchmany`, 비-`CONNECTION_CLOSED` `McpError`, Timeout `reason`)

* 심각도: Medium — 1차 수정(발견 2)이 `cursor.execute()`의 `pyodbc.Error`와 Tool `isError` 결과의 `TextContent`는 정제했지만, 세 부분이 비어 있었다.
  1. `readonly_query_executor.execute()`에서 `cursor.execute()` 성공 이후의 `cursor.description` 접근과 `cursor.fetchmany()`는 `pyodbc.Error` 처리 경계 밖에 있어, 이 단계의 실패는 원본 Driver 예외가 그대로 `anyio.to_thread.run_sync()`를 거쳐 FastMCP까지 전달될 수 있었다.
  2. `MCPClientManager._call_tool()`이 `CONNECTION_CLOSED`가 아닌 `McpError`를 `raise`로 그대로 다시 던져, MCP SDK 내부 예외 타입과 원본 `message`/`data`가 Backend 공개 경계(`app/mcp/client_manager.py`가 정의한 3개 예외 타입) 밖으로 노출됐다.
  3. Timeout과 일반 Tool 오류가 둘 다 `reason="tool_error"`였고 메시지 문자열(`"MCP tool reported a timeout"` vs `"MCP tool returned an error"`)로만 구분할 수 있어, 호출자가 `reason` 하나만 보고 프로그램적으로 구분할 방법이 없었다. Allowlist도 "timeout" 단어 포함 여부만 검사해 서버가 만들지 않은 임의의 "timeout" 언급까지 Timeout으로 잘못 분류될 여지가 있었다.
* 실제 수정 내용:
  1. `mcp_server/readonly_query_executor.py`의 `execute()`: `connection.timeout` 설정·`connection.cursor()`·`cursor.execute()`·`cursor.description` 접근·`cursor.fetchmany()`를 모두 하나의 `try: ... except pyodbc.Error as exc:` 경계 안으로 옮겼다. `row_count`/`truncated`/`execution_ms` 계산과 반환 형식은 그대로 유지했다.
  2. `app/mcp/client_manager.py`의 `_call_tool()`: `CONNECTION_CLOSED`가 아닌 `McpError`를 `raise MCPToolExecutionError(_SAFE_PROTOCOL_ERROR_MESSAGE, reason="tool_protocol_error") from exc`로 변환한다(`_SAFE_PROTOCOL_ERROR_MESSAGE = "MCP protocol error"`, 원본 `message`/`data` 미포함). `unavailable`은 바꾸지 않는다 — Transport 단절로 확인된 것이 아니기 때문이다.
  3. `_classify_tool_error_message()`를 `_classify_tool_error()`로 바꿔 `(메시지, reason)` 튜플을 반환한다. Allowlist를 `_TIMEOUT_SAFE_PHRASES = ("DB query timeout exceeded", "Schema inspection timeout exceeded")` 두 개의 고정 Phrase에 대한 부분 문자열 포함 검사로 좁혔다(FastMCP의 Tool 실행 오류 Prefix를 고려해 정확한 전체 일치가 아니라 부분 포함으로 확인). 일치하면 `reason="tool_timeout"`, 그 외 모든 `isError` 결과는 `reason="tool_error"`다.
* 추가한 회귀 테스트:
  * `tests/test_mcp_readonly_query_executor.py::test_execute_does_not_leak_raw_pyodbc_error_text_from_fetchmany`, `test_fetchmany_timeout_is_distinguished_from_generic_failure`: `cursor.execute()`는 성공하지만 `cursor.fetchmany()`가 Secret-like Marker를 담은 `pyodbc.Error`를 던지는 Fake로 `RuntimeError`/`TimeoutError` 메시지에 원문이 없음과 Timeout 구분을 확인.
  * `tests/test_mcp_client_manager.py::test_mcp_error_with_other_code_is_converted_to_tool_protocol_error`(Secret-like Marker를 담은 `message`/`data`를 가진 Fake `McpError`가 `MCPToolExecutionError(reason="tool_protocol_error")`로 변환되고 Marker가 메시지에 없으며 `unavailable`이 그대로 `False`임을 확인), `test_mcp_error_with_other_code_does_not_expose_sdk_exception_type`(원본 `McpError`가 호출자에게 노출되지 않음을 `except McpError: assert False` 패턴으로 확인).
  * `tests/test_mcp_client_manager.py::test_tool_error_with_safe_timeout_phrase_is_classified_as_tool_timeout`(안전 Phrase 2종 + FastMCP Prefix가 붙은 경우까지 3가지 매개변수화, 모두 `reason="tool_timeout"`), `test_tool_error_with_generic_timeout_word_is_not_classified_as_tool_timeout`("timeout"이라는 단어만 있고 안전 Phrase가 아니면 `reason="tool_error"`로 유지됨을 확인 — 기존에는 이 케이스가 `tool_timeout`으로 잘못 분류됐을 것이다), `test_tool_error_without_timeout_text_is_classified_as_generic`(기존 유지, `reason` 검사 추가).
  * 기존 `test_mcp_error_with_other_code_is_not_treated_as_transport_error`(원본 `McpError` 그대로 전파를 기대)는 위 새 동작에 맞춰 `test_mcp_error_with_other_code_is_converted_to_tool_protocol_error`로 대체했다.
* 검증 결과: 위 테스트 전부 통과(`test_mcp_readonly_query_executor.py` 39개, `test_mcp_client_manager.py` 21개). 이 발견에 대한 실제 Docker MSSQL 전용 신규 테스트는 추가하지 않았다 — `fetchmany()` 실패, 비-`CONNECTION_CLOSED` `McpError`, 임의의 "timeout" 단어 포함 오류는 모두 Fake로 정확하게 재현 가능한 조건이고 실제 DB에서 이런 조건을 안정적으로 만들 방법이 없어(예: `fetchmany()`만 선택적으로 실패시키는 실제 DB 상황을 재현하기 어려움) 단위 테스트가 더 적합하다고 판단했다. 기존 `test_mcp_real_target_db.py`의 정상 경로 테스트들이 이번 수정 이후에도 여전히 통과함을 실제 DB로 확인했다(회귀 없음).
* 상태: Resolved(3차 Codex 재검토에서 확인)

## Codex 구현 검토 발견 사항과 수정(3차)

3차 Codex 재검토에서 2차 수정 2건(정확한 자식 프로세스 종료, `fetchmany`/비-`CONNECTION_CLOSED` `McpError`/Timeout `reason` 오류 경계 완성)은 Resolved로 확인됐다. 대신 `mcp_server/tools/inspect_schema.py`에서 2차 완료 보고 때 "이번 작업 범위 밖"으로 남겨뒀던 동일 계열의 위험이 실제 발견 사항으로 지적되어 이번에 수정했다. 공개 경계·Contract·Plan을 바꾸지 않는 구현 버그 수정이므로 사용자 재승인 없이 직접 수정했다.

### 발견 — `_inspect_schema_sync()`의 `connection.timeout` 설정과 `connection.cursor()` 호출이 `pyodbc.Error` 처리 범위 밖에 있음

* 심각도: Medium — `readonly_query_executor.execute()`의 `fetchmany` 문제(2차 발견 B)와 같은 유형이다. `connection.timeout = db.SCHEMA_INSPECTION_TIMEOUT_SECONDS` 대입과 `connection.cursor()` 호출이 4개 카탈로그 Query를 감싸는 안쪽 `try: ... except pyodbc.Error` 밖(바깥쪽 `try`만) 있어, 이 두 지점에서 `pyodbc.Error`가 나면 원본 Driver 오류 문자열이 정제되지 않은 채 `anyio.to_thread.run_sync()`를 거쳐 FastMCP까지 전달될 수 있었다. Plan의 "원본 Tool/Driver 오류 문자열을 그대로 노출하지 않는다"는 원칙과 어긋난다.
* 실제 수정 내용: `mcp_server/tools/inspect_schema.py`의 `_inspect_schema_sync()`에서 `connection.timeout` 설정과 `connection.cursor()` 호출을 안쪽 `try` 블록 맨 앞으로 옮겨, 4개 카탈로그 Query의 `execute`/`fetchall`과 함께 하나의 `try: ... except pyodbc.Error as exc:` 경계 안에 두었다. Timeout은 기존과 동일하게 `TimeoutError("Schema inspection timeout exceeded")`로, 그 외는 `RuntimeError("Schema inspection failed")`로 변환하며 두 메시지 모두 `str(exc)`나 원본 Driver 문자열을 포함하지 않는다. `connection.close()`를 보장하는 바깥쪽 `try/finally` 구조는 그대로 유지했다. SQL 4개 Query, Catalog 조립 로직, 반환 구조(Contract)는 전혀 바꾸지 않았다 — `connection.timeout`/`cursor()` 두 줄의 위치만 이동했다.
* 추가한 회귀 테스트(기존 `tests/test_mcp_inspect_schema_unit.py`의 `_RaisingConnection`/`_RaisingCursor` Fake 패턴을 재사용, 새 Test Infrastructure 없음):
  * `test_inspect_schema_does_not_leak_raw_pyodbc_error_text_from_timeout_assignment`: `connection.timeout` 대입 자체가 Secret-like Marker(`PWD=hunter2;SERVER=internal-host,1433` 포함)를 담은 `pyodbc.Error`를 던지는 `_TimeoutAssignmentRaisingConnection` Fake로 `RuntimeError` 메시지에 원문이 없음을 확인.
  * `test_inspect_schema_does_not_leak_raw_pyodbc_error_text_from_cursor_call`: `connection.cursor()` 호출 자체가 같은 형태의 `pyodbc.Error`를 던지는 `_CursorCallRaisingConnection` Fake로 동일하게 확인.
  * `test_inspect_schema_still_distinguishes_timeout_at_cursor_call`: `connection.cursor()` 호출에서 SQLSTATE `HYT00`(Timeout)이 나면 여전히 `TimeoutError`로 구분되는지 확인(`connection.timeout` 대입 지점은 기존 `test_inspect_schema_still_distinguishes_timeout_from_generic_failure` 등과 원리가 같아 중복 추가하지 않았다).
* 검증 결과: `tests/test_mcp_inspect_schema_unit.py` 7개 전부 통과(신규 3개 + 기존 4개). `uv run pytest -q -m "not requires_target_db"` 162 passed, `uv run pytest -q` 172 passed. 실제 Docker MSSQL로 `test_inspect_schema_returns_adventureworks_user_schemas`를 다시 실행해 정상 Schema Inspection 결과(회귀 없음)를 확인했다. `git diff --check`와 변경 파일(`mcp_server/tools/inspect_schema.py`, `tests/test_mcp_inspect_schema_unit.py`) 후행 공백 검사 모두 통과.
* 상태: Resolved(Codex 재검토에서 확인)

## Plan 준수 및 차이

Approved Plan과 일치한 결정:

* 대상 DB 연결·Read-Only 경계(`mcp_server/db.py`만 `TARGET_DB_*` 소유, `data_agent_ro`의 SELECT-only 권한이 실제 경계, `ApplicationIntent=ReadOnly`는 보안 장치 아님).
* MCP SDK 사용 방식(공식 SDK만, `async def` Tool + `anyio.to_thread.run_sync()`, `dict[str, Any]`+`structured_output=True`, `structuredContent`만 소비).
* FastAPI Lifespan과 MCP Lifecycle 결합 순서, `asyncio.timeout(30)` 범위, `verify_tool_contracts()`.
* Physical Metadata Catalog를 Startup 1회 생성해 메모리에만 보관(Admin DB 미저장).
* `inspect_schema`의 시스템 객체 제외, PK/FK 순서 보존, `MS_Description` 원문 수집.
* `execute_readonly_query`의 최소 SQL 검사 키워드 목록, 입력 상한(1~15초/1~500행), Query Timeout 분리 적용, 직렬화 규칙.
* `MCPClientManager`의 Lock+재확인, Timeout·Transport 오류에 따른 `unavailable` 전환, 자동 재연결 없음, 예외 3종의 위치(`app/mcp/client_manager.py`에만 존재).
* Timeout·상한 확정값 5개 전부(시작 30초, Call 20초, Schema Inspection 15초, Query 1~15초, 행 1~500).
* 의존성 버전(`mcp>=1.28,<2`, `pyodbc>=5.3,<6`, `cli` Extra 미포함).

구현하지 못했거나 명시적으로 제외한 Plan 항목:

* 없음 — Plan 2~9절에 명시된 구현 범위는 모두 완료했다.

Plan 수정·재승인이 필요했던 차이와 처리 결과:

* 차이 없음. 이 문서에 기록한 모든 차이(`TASK-003`의 `sys.types` Join 수정·FK Grouping Key 수정·`pyodbc.Error` 처리 경계 확장, `TASK-005`의 `MCPTransportError.reason` 단순화·Transport 예외 종류 확장·`MCPToolExecutionError.reason`에 `tool_timeout`/`tool_protocol_error` 추가, `TASK-007`의 하위 프로세스 기동 방식과 `env` 상속 추가, `TASK-009`의 `correlation_id` 고정값, `TASK-011`의 Fake Fixture 배선 방식, "Codex 구현 검토 발견 사항과 수정(1차)" 5건·"(2차)" 2건·"(3차)" 1건)는 Plan이 고정하지 않은 Private Helper·테스트 인프라 수준의 결정이거나 그 범위 안에서의 버그 수정·방어 강화다. 공개 경계·Contract·보안 경계·요구사항을 바꾸지 않아 Plan을 수정하지 않고 진행했다.

## Feature 전체 검증

* [x] 모든 Spec 요구사항이 실제 구현과 검증에 연결됨
* [x] 모든 Plan 설계가 구현 또는 명시적으로 제외됨(제외 항목 없음)
* [x] 관련 자동 테스트 통과(172 passed — 실제 DB 10개 포함, 1·2·3차 Codex 검토 수정에 대한 회귀 테스트 포함)
* [x] 필요한 수동 검증 완료(오답 비밀번호 `stderr`/`stdout` 비노출 2건, 실제 FastAPI Lifespan에서 Physical Metadata Catalog 메모리 적재 확인)
* [x] 실행하지 못한 검증과 남은 위험 기록(아래 참고)
* [x] 필수 Codex 구현 검토 완료 — **1·2·3차 검토에서 나온 발견 사항이 모두 Resolved로 확인됐고 전체 자동 테스트와 수동 검증이 통과했다. 이 문서의 Status는 `Verified`다.**

## 최종 구현 검토

1차 Codex 구현 검토에서 5건, 2차 재검토에서 신규 2건, 3차 재검토에서 신규 1건이 나왔고 전부 수정했다. 모든 발견 사항은 후속 Codex 재검토에서 Resolved로 확인됐다(자세한 내용은 "Codex 구현 검토 발견 사항과 수정(1차)"/"(2차)"/"(3차)" 절).

| Reviewer | 발견 사항 | 심각도 | 처리 Task 또는 기각 근거 | 상태 |
|---|---|---|---|---|
| Codex(1차) | 실제 MCP Transport 종료(`McpError(CONNECTION_CLOSED)`, `anyio` 스트림 예외)를 `OSError`/`EOFError`만으로는 감지하지 못함 | High | `TASK-005`: 예외 처리 확장, 실제 Mid-call 하위 프로세스 종료로 회귀 검증 | Resolved |
| Codex(1차) | `pyodbc` 원본 Driver 오류 문자열과 Tool의 임의 `TextContent`가 Backend 예외 메시지에 그대로 노출될 수 있었음 | High | `TASK-002`/`TASK-003`/`TASK-005`: 고정 안전 메시지 + Timeout Allowlist 분류로 치환(주요 경로). `fetchmany`·비-`CONNECTION_CLOSED` `McpError` 경계는 2차 발견 B에서, `inspect_schema.py`의 나머지 경계는 3차 발견에서 마저 처리 | Resolved(2·3차 수정 포함) |
| Codex(1차) | 부모 프로세스 OS 환경변수가 자식 MCP Server에 상속되지 않아 "OS 환경변수가 `.env`보다 우선"이 자식에서 성립하지 않음 | Medium | `TASK-007`: `StdioServerParameters(env=dict(os.environ))` 추가 | Resolved |
| Codex(1차) | Foreign Key Grouping Key가 `fk.name`만 사용해 서로 다른 Schema/Table의 동일 이름 FK가 합쳐질 수 있음 | Medium | `TASK-003`: Grouping Key를 `fk.object_id`로 변경 | Resolved |
| Codex(1차) | `rstrip(";")`가 후행 세미콜론을 모두 제거해 `SELECT 1;;;`이 통과함 | Low | `TASK-002`: 후행 세미콜론 하나만 제거하도록 수정 | Resolved |
| Codex(2차) | Mid-call 프로세스 종료 테스트가 Command Line Pattern으로 시스템 전체 프로세스를 종료할 위험 | High(테스트 안전성) | "Codex 구현 검토 발견 사항과 수정(2차)" 발견 A: `_create_platform_compatible_process`를 감싸 정확한 `Process` 객체 하나만 캡처·`kill()` | Resolved |
| Codex(2차) | `fetchmany`·비-`CONNECTION_CLOSED` `McpError`·Timeout `reason` 구분을 포함한 Tool 오류 경계 불완전 | Medium | "Codex 구현 검토 발견 사항과 수정(2차)" 발견 B: `fetchmany`를 오류 경계에 포함, `McpError`를 `MCPToolExecutionError(reason="tool_protocol_error")`로 변환, Timeout을 `reason="tool_timeout"`으로 구분하고 Allowlist를 고정 Phrase로 좁힘 | Resolved |
| Codex(3차) | `_inspect_schema_sync()`의 `connection.timeout` 설정과 `connection.cursor()` 호출이 `pyodbc.Error` 처리 범위 밖에 있어 원본 Driver 오류가 노출될 수 있음 | Medium | "Codex 구현 검토 발견 사항과 수정(3차)": 두 지점을 4개 Query와 같은 `try: ... except pyodbc.Error` 경계 안으로 이동 | Resolved |

## 최종 검증 기록

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 전체 자동 테스트 | `uv run pytest -q` | 통과 (172 passed, 1 warning) |
| `requires_target_db` 제외 | `uv run pytest -q -m "not requires_target_db"` | 통과 (162 passed, 10 deselected) |
| `requires_target_db`만 | `uv run pytest -q -m requires_target_db` | 통과 (10 passed, 162 deselected) |
| `inspect_schema` 단위(3차 Codex 재검토) | `uv run pytest -q tests/test_mcp_inspect_schema_unit.py` | 통과 (7 passed) |
| 실제 DB — Schema Inspection(3차 수정 이후 회귀 확인) | `test_mcp_real_target_db.py::test_inspect_schema_returns_adventureworks_user_schemas` | 통과 |
| 사용자 수동 검증 — FastAPI 메모리 Catalog | 실제 `main.app` Lifespan 기동 후 `app.state.physical_metadata_catalog` 조회 | 통과 — `PhysicalMetadataCatalog`, Schema 6개, Table 71개, Physical FK 90개 및 `Production.Product` Metadata 확인 |
| 실제 DB — 행 제한/Truncation | `test_mcp_real_target_db.py::test_execute_readonly_query_enforces_maximum_returned_rows`, `..._returns_untruncated_when_within_limit` | 통과 |
| 실제 DB — Parameter Binding | `test_mcp_real_target_db.py::test_execute_readonly_query_binds_parameters` | 통과 |
| 실제 DB — 쓰기 거부 | `test_mcp_real_target_db.py::test_data_agent_ro_account_rejects_write_at_db_level` | 통과 |
| 실제 DB — Query Timeout 실제 적용 | `test_mcp_real_target_db.py::test_execute_sets_connection_timeout_to_query_timeout_seconds` | 통과 |
| 실제 DB — MCP Lifecycle Smoke | `test_mcp_real_target_db.py::test_mcp_lifecycle_smoke_end_to_end` | 통과 |
| 실제 DB — 전체 `main_app` Startup(Fake 없음) | `test_mcp_real_target_db.py::test_app_startup_with_real_mcp_populates_state_and_cleans_up_on_shutdown` | 통과 |
| 실제 DB — OS 환경변수가 `.env`보다 자식 프로세스에서도 우선(1차 Codex 검토) | `test_mcp_real_target_db.py::test_real_child_process_prioritizes_os_env_override_over_dotenv` | 통과 |
| 실제 DB — Mid-call 하위 프로세스 종료 시 Transport 오류 변환, 정확한 Process 객체만 종료(1·2차 Codex 검토) | `test_mcp_real_target_db.py::test_mid_call_subprocess_termination_raises_transport_error_and_marks_unavailable`(3회 반복 실행, 매번 통과. 실행 후 매번 잔여 `mcp_server.server` 프로세스 수동 확인 — 0건) | 통과 |
| 수동 — 오답 비밀번호로 `db.verify_connection()` | `uv run python -c "..."`(출력에 비밀번호 원문 없음 확인) | 통과 |
| 수동 — 오답 비밀번호로 `python -m mcp_server.server` 실제 하위 프로세스 | `subprocess.run(...)`(stdout/stderr 모두 비밀번호 원문 없음 확인) | 통과 |
| 시스템 전체 프로세스 검색 코드 잔존 여부(2차 Codex 재검토) | `tests/`, `mcp_server/`, `app/` 전체에서 `Get-CimInstance`/`CommandLine`/`Stop-Process`/`powershell` 문자열 검색 | 통과(발견 없음) |
| 서식 — 공백 오류 | `git add -N`로 신규 파일을 추적 대상으로 표시한 뒤 `git diff --check`, 이후 `git reset`으로 다시 Unstage | 통과(CRLF 정보성 경고만, 오류 없음) |
| Secret 미노출(실제 값) | `.env`의 `*_PASSWORD` 값을 읽어(출력하지 않고) `app/`, `mcp_server/`, `tests/`, `docs/features/0003-mcp-readonly-data-access/`, `pyproject.toml` 전체에서 원문 포함 여부 정적 검색 | 통과(발견 없음) |
| Secret-like Marker 사용 확인 | `tests/test_mcp_*.py`에 쓰인 `SECRET-MARKER-*`/`hunter2`/`internal-host`/`definitely_not_a_real_login_xyz` 등은 모두 테스트가 만든 합성 문자열이며 실제 `.env` 값이 아님을 코드 확인 | 통과 |
| 변경 파일 범위 | `git status --porcelain`, `git diff --stat -- main.py app/core/config.py docs/architecture/project-structure.md app/api/` | Plan이 변경 금지한 4개 대상 변경 없음 확인. `docs/adr/*`, `docs/contracts/*`, `docs/mvp/roadmap.md`는 이 작업 시작 전/작업과 무관하게 이미 존재하던 외부 변경이며 이번 구현에서도 손대지 않음 |
| 문서 링크 | 이 파일의 상대 링크(`./spec.md`, `./plan.md`) 확인, `spec.md`/`plan.md` 미수정 확인 | 통과 |

실행하지 못한 검증과 남은 위험:

* **AWS 배포 환경 검증 없음**: Docker 로컬 MSSQL로만 검증했다. 실제 배포 환경(예: RDS/EC2 대상 DB, 다른 네트워크 지연·방화벽 조건)에서의 동작은 검증 범위 밖이다(Plan도 이를 명시적으로 범위 밖으로 뒀다).
* **동시 다중 요청의 실제 부하 검증 없음**: `MCPClientManager`의 Lock 직렬화는 단위 테스트(Fake, 2개 동시 호출)로만 확인했다. 실제 여러 FastAPI 요청이 짧은 시간에 몰릴 때의 지연이나 처리량은 측정하지 않았다(Plan 범위 밖 — NFR에 성능 목표 없음).
* **`MCPTransportError`의 `subprocess_exited` 개별 식별은 여전히 하지 않음**: `(OSError, EOFError)`뿐 아니라 `McpError(CONNECTION_CLOSED)`·`anyio` 스트림 예외까지 잡도록 넓혔고, 2차 재검토에서도 정확한 Process 객체를 이용한 실제 Mid-call 종료로 이 경로를 다시 검증했지만, 이 모든 경우를 여전히 `reason="connection_closed"` 하나로 합쳐 처리한다(실측으로도 하위 프로세스 종료가 별도 신호가 아니라 `McpError(CONNECTION_CLOSED)`로 관측되어 지금 시점에는 구분할 근거가 없다). Fail Closed 동작 자체(감지·`unavailable` 전환·재사용 안 함)는 이번 수정과 실제 Kill 테스트로 보장을 확인했다.
* **`data_agent_ro` 권한 범위의 전수 확인 없음**: 이번 검증은 `UPDATE ... WHERE 1 = 0` 한 문장으로 쓰기 거부만 확인했다. `INSERT`/`DELETE`/DDL 등 다른 쓰기 유형이나 다른 Schema/Table에 대한 권한까지 전수 확인하지는 않았다(DB 계정 자체의 권한 부여 범위는 이 Feature의 구현 대상이 아니라 사전 조건이다).
* **`sys.types` 권한 문제가 다른 UDT나 다른 Catalog View에도 존재할 가능성**: 이번에 발견한 문제는 `sys.types`에 국한해 수정했다. `sys.extended_properties`, `sys.key_constraints` 등 다른 Catalog View에서도 유사한 Metadata 가시성 제한이 있는지는 이번 AdventureWorks2022 데이터로 관찰된 범위(FK 90건, PK 정상 조회, Description 76건 수집)에서는 문제가 없었으나, 다른 DB나 다른 권한 구성에서 유사 문제가 재발할 가능성은 배제하지 않는다.

## Verified 상태 조건

* [x] 모든 필수 구현과 검증이 완료됨
* [x] Spec Acceptance Criteria와 Plan 준수 여부가 확인됨
* [x] Plan과의 차이가 모두 이 문서에 근거와 함께 기록됨(재승인이 필요한 차이는 없음)
* [x] Codex 구현 검토 결과가 해결되거나 명시적으로 기각됨 — **1·2·3차 검토에서 나온 발견 사항 8건 모두 Resolved 확인**
* [x] 실제 변경, 테스트 결과와 남은 위험이 이 문서와 일치함
