# Admin DB 기반 Tasks

* Feature ID: `FEAT-0002`
* Status: `Verified`
* Development Track: `Standard`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)
* Source Plan: [`./plan.md`](./plan.md) (`Approved`)

## 구현 요약

Approved Plan대로 대상 AdventureWorks2022와 분리된 SQLite Admin DB 기반을 구현했다. `Settings.admin_db_path`(env `ADMIN_DB_PATH`, 기본값 `./data/admin.db`)로 경로를 주입하고, FastAPI Lifespan이 경로 확인 → SQLAlchemy 2.0 동기 Engine 생성(FK Pragma 활성화) → Alembic `upgrade head` → head Revision·4개 필수 테이블 확인 순서로 Admin DB를 준비한다. 성공하면 `Engine`/`sessionmaker`를 `app.state`에 저장하고, 실패하면 `AdminDBUnavailableError`가 전파되어 ASGI `startup`이 완료되지 않는다. `users`, `table_policies`(JSON 단일 행), `audit_logs`, `error_reports`(복합 Foreign Key) 4개 테이블과 제약을 Alembic 초기 Revision과 SQLAlchemy ORM 모델로 구현했다. Repository, Service, Audit Writer, Seed 데이터, MCP·대상 DB 연결은 구현하지 않았다.

## 요구사항 Coverage

| Spec 요구사항 | Plan 절 | 실제 구현 Task | 검증 결과 |
|---|---|---|---|
| `FR-001` | 2절 | `TASK-001`, `TASK-002` | 통과 |
| `FR-002` | 1절 | `TASK-001` | 통과 |
| `FR-003` | 3절 | `TASK-003` | 통과 |
| `FR-004` | 4절 | `TASK-004` | 통과 |
| `FR-005` | 4절 | `TASK-004` | 통과 |
| `FR-006` | 5절 | `TASK-005` | 통과 |
| `FR-007` | 5절 | `TASK-005` | 통과 |
| `FR-008` | 5절 | `TASK-005` | 통과 |
| `FR-009` | 6절 | `TASK-006` | 통과 |
| `FR-010` | 6절 | `TASK-006` | 통과 |
| `FR-011` | 6절 | `TASK-006` | 통과 |
| `FR-012` | 7절 | `TASK-007` | 통과 |
| `FR-013` | 전체 | `TASK-001`~`TASK-008` | 통과(`pytest` 52개) |
| `NFR-001` | 2절 | `TASK-002` | 통과(코드 리뷰) |
| `NFR-002` | 3절 | `TASK-003` | 통과 |
| `NFR-003` | 1절 | `TASK-002` | 통과(코드 리뷰, 잠금·다중 프로세스 조정 코드 미추가) |
| `NFR-004` | 1절 | `TASK-001` | 통과 |
| `NFR-005` | 6절 | `TASK-006` | 통과(코드 리뷰, `audit_logs`에 secret/prompt/result 전용 필드 없음) |

## `TASK-001` Admin DB 경로 설정과 배포 결정

* Status: `Completed`
* 요구사항: `FR-001`, `FR-002`, `NFR-004`
* 실제 변경 파일:
  * `app/core/config.py`
  * `data/.gitkeep`
  * `.gitignore`

구현 결과:

* `Settings.admin_db_path: str = "./data/admin.db"` 필드를 추가하고 `field_validator`로 빈 문자열/공백을 거부한다.
* 저장소에 `data/.gitkeep`을 추가해 기본 경로의 부모 디렉터리를 클론 시점부터 보장한다.
* `.gitignore`에 `data/*.db*`를 추가해 실제 SQLite 파일(및 `-journal`/`-wal` 등 부속 파일)을 버전 관리에서 제외한다.
* 애플리케이션은 부모 디렉터리를 자동 생성하지 않는다(`app/db/session.py`, TASK-002).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_admin_db_config.py -q`
* 결과: 통과 (4 passed) — 기본값, 사용자 지정 값, 빈 문자열/공백 거부(2개 값 매개변수화) 확인.
* 수동 검증: `git check-ignore -v data/admin.db` → `.gitignore:22:data/*.db*  data/admin.db`로 무시 확인. `data/admin.db-journal`도 동일하게 무시 확인. `data/.gitkeep`은 무시되지 않음(exit 1) 확인.

Plan과의 차이:

* 없음

Reviewer 의견과 처리:

* 미검토

## `TASK-002` SQLAlchemy Engine·Session과 FK 활성화

* Status: `Completed`
* 요구사항: `FR-001`, `NFR-001`, `NFR-003`
* 실제 변경 파일:
  * `app/db/__init__.py`
  * `app/db/errors.py`
  * `app/db/session.py`

구현 결과:

* `AdminDBUnavailableError(RuntimeError)`를 정의했다.
* `build_admin_db_engine(admin_db_path)`가 부모 디렉터리 존재·쓰기 가능 여부를 확인한 뒤(`_ensure_parent_directory_accessible`), `sqlalchemy.URL.create("sqlite", database=...)`로 SQLite Engine을 생성한다(Windows 경로의 드라이브 문자·역슬래시 문제를 피하기 위해 문자열 결합 대신 `URL.create` 사용).
* `Engine`의 `connect` 이벤트에서 `PRAGMA foreign_keys=ON`을 실행해 모든 커넥션에 FK 강제를 켠다.
* `get_sessionmaker(engine)`이 `sessionmaker(bind=engine, expire_on_commit=False)`를 반환한다.
* 대상 MSSQL Driver나 MCP 관련 코드는 포함하지 않았다.
* 여러 인스턴스가 하나의 SQLite 파일을 공유하기 위한 잠금·조정 코드는 추가하지 않았다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_admin_db_lifecycle.py -q`
* 결과: 통과 (3 passed) — startup 시 Engine/Sessionmaker가 `app.state`에 채워짐, FK 강제가 켜진 상태에서 필수 테이블 확인.
* 수동 검증: `uv run python -c "..."`로 Engine 생성 후 `PRAGMA foreign_keys` 값이 켜져 있는지, `error_reports`/`table_policies` 관련 제약 위반이 `IntegrityError`로 거부되는지 직접 확인(아래 TASK-005~007의 자동 테스트로 대체 확인됨).

Plan과의 차이:

* 없음

Reviewer 의견과 처리:

* 미검토

## `TASK-003` Alembic Migration과 최소 Schema 확인

* Status: `Completed`
* 요구사항: `FR-002`, `FR-003`, `NFR-002`
* 실제 변경 파일:
  * `alembic.ini`
  * `alembic/env.py`
  * `alembic/script.py.mako`
  * `alembic/versions/0001_admin_db_foundation.py`
  * `app/db/schema.py`
  * `app/core/lifespan.py`

구현 결과:

* `app/db/schema.py`의 `prepare_admin_db_schema(engine)`이 (1) `_run_migrations`: 애플리케이션이 만든 `Engine`의 Connection을 `Config.attributes["connection"]`으로 Alembic에 전달해 `command.upgrade(config, "head")`를 실행하고, (2) `_verify_schema`: `ScriptDirectory`의 head Revision과 `MigrationContext`의 현재 Revision이 일치하는지, `users`/`table_policies`/`audit_logs`/`error_reports` 4개 테이블이 존재하는지 확인한다. 두 단계 중 하나라도 실패하면 `AdminDBUnavailableError`로 변환한다.
* `alembic/env.py`는 `config.attributes.get("connection")`이 있으면 그대로 재사용하고, 없으면(수동 CLI 실행) `alembic.ini`의 `sqlalchemy.url`로 새 Engine을 만든다. `fileConfig` 호출은 의도적으로 제거했다(아래 "Plan과의 차이" 참고).
* `app/core/lifespan.py`가 `get_settings()` → `build_admin_db_engine()` → `prepare_admin_db_schema()` → `app.state` 저장 순서로 연결되고, `prepare_admin_db_schema` 실패 시 `engine.dispose()` 후 예외를 다시 던진다. 정상 종료 시에도 `finally`에서 `engine.dispose()`한다.
* 컬럼 타입 비교, CHECK SQL 문자열 비교, Unique/Index 이름 비교, Trigger 존재 검사, 전체 Schema Diff, 수동 DB 변조 탐지를 위한 별도 런타임 검증 시스템은 Plan대로 만들지 않았다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_admin_db_lifecycle.py tests/test_admin_db_startup_failure.py -q`
* 결과: 통과 (5 passed) — 최초 Migration, 반복 Migration의 멱등성과 기존 데이터 보존, head Revision 일치, 경로 접근 불가·비호환 Schema(사전에 존재하는 `users` 테이블과 충돌) 시 startup 실패.
* 수동 검증: 기본 경로(`./data/admin.db`)로 두 번 연속 기동 → 두 번째 기동에서 첫 번째 기동이 저장한 `MANUAL-1` 사용자 행이 유지됨을 확인 후 파일 삭제로 정리. `ADMIN_DB_PATH`를 존재하지 않는 디렉터리로 설정해 기동 시도 → `AdminDBUnavailableError`로 실패하고 원인 메시지(부모 디렉터리 없음)가 출력됨을 확인.

Plan과의 차이:

* Plan에는 없던 세부 구현 결정: `alembic/env.py`에서 표준 Alembic 템플릿의 `fileConfig(config.config_file_name)` 호출을 제거했다. `fileConfig`의 기본 동작(`disable_existing_loggers=True` 및 Root Logger 핸들러 재구성)이 이미 존재하는 `app.core.lifespan` 로거를 비활성화하고 Root Logger 핸들러를 교체해, `Migration을 한 번이라도 실행한 뒤에는 애플리케이션·테스트의 기존 로깅이 깨지는 부작용이 있었다(`tests/test_app_lifecycle.py`의 시작·종료 로그 캡처 테스트가 이 문제로 실패하는 것을 발견하고 원인을 확인함). 이 Feature와 Plan 어디에도 Alembic 로깅 설정에 대한 요구가 없으므로, 로깅 설정 없이 Migration만 수행하도록 `fileConfig` 호출과 `alembic.ini`의 로깅 관련 섹션을 제거했다. 공개 경계·요구사항·파일 책임에 영향이 없는 구현 세부 결정이라 판단해 Plan을 수정하지 않고 진행했다.

Reviewer 의견과 처리:

* 미검토

## `TASK-004` users 모델과 제약

* Status: `Completed`
* 요구사항: `FR-004`, `FR-005`
* 실제 변경 파일:
  * `app/models/base.py`
  * `app/models/user.py`
  * `alembic/versions/0001_admin_db_foundation.py`(users 테이블 부분)

구현 결과:

* `UserRole(str, Enum)`(`supply_risk_analyst`, `inventory_viewer`)와 공유 헬퍼 `user_role_type()`을 `app/models/user.py`에 정의했다. `values_callable`로 소문자 `.value`를 저장하고 `validate_strings=True`로 ORM 대입 경로를 검증하며, `create_constraint=False`로 SQLAlchemy의 암묵적 CHECK 생성을 끄고 Alembic Migration의 명시적 `ck_users_role` CheckConstraint 하나로 DB 제약을 통일했다.
* `User` 모델과 Migration에 `slack_user_id`(`UNIQUE`, `CHECK(length(trim(...))>0)`), `is_active`(`NOT NULL`, `server_default='1'`, `CHECK(is_active IN (0,1))`, `Boolean(create_constraint=False)`로 SQLAlchemy 중복 CHECK 방지), `role`(`NOT NULL`, 기본값 없음)을 구현했다.
* 별도 `roles`/`user_roles` 테이블과 Seed 사용자는 만들지 않았다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_user_model.py -q`
* 결과: 통과 (6 passed) — 허용 역할 저장 시 소문자 value 확인(2개 역할 매개변수화), 알 수 없는 역할의 DB CHECK 거부, 중복/공백 `slack_user_id` 거부, `is_active` 기본값과 Boolean CHECK 거부.

Plan과의 차이:

* 없음

Reviewer 의견과 처리:

* 미검토

## `TASK-005` table_policies 모델과 제약

* Status: `Completed`
* 요구사항: `FR-006`, `FR-007`, `FR-008`
* 실제 변경 파일:
  * `app/models/table_policy.py`
  * `alembic/versions/0001_admin_db_foundation.py`(table_policies 테이블 부분)

구현 결과:

* `TablePolicy`를 JSON 단일 행 구조(`allowed_columns: Mapped[list[str]]`, SQLAlchemy `JSON` 타입)로 구현했다. `table_policy_columns` 자식 테이블이나 `before_flush` 가드는 만들지 않았다.
* DB CHECK(`ck_table_policies_allowed_columns_nonempty_array`)가 `json_valid`, `json_type(...) = 'array'`, `json_array_length(...) >= 1`을 강제하고, `UNIQUE(role, schema_name, table_name)`으로 조합당 정책 하나를 보장한다. `role`은 `users`와 동일한 `user_role_type()`/명시적 CheckConstraint를 재사용한다.
* ORM `@validates("allowed_columns")`가 원소 문자열 타입, trim 후 빈 문자열, `"*"` Wildcard, 중복 컬럼명을 거부한다. 이 검증은 ORM 경로에서만 적용되며 DB CHECK가 이를 대신하지 않는다는 Plan의 책임 구분을 그대로 구현했다.
* 정책·컬럼 부재를 "허용"으로 표현하는 플래그나 Nullable 컬럼은 스키마에 없다. 대상 DB Schema 동기화 코드도 없다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_table_policy_model.py -q`
* 결과: 통과 (7 passed) — JSON 배열 저장, 정책 중복 거부(DB UNIQUE), 빈 배열/유효하지 않은 JSON·비배열 거부(DB CHECK, 원시 SQL 경로), Wildcard·공백·중복 컬럼명 거부(ORM `@validates`).

Plan과의 차이:

* 없음

Reviewer 의견과 처리:

* 미검토

## `TASK-006` audit_logs 모델과 제약

* Status: `Completed`
* 요구사항: `FR-009`, `FR-010`, `FR-011`, `NFR-005`
* 실제 변경 파일:
  * `app/models/audit_log.py`
  * `alembic/versions/0001_admin_db_foundation.py`(audit_logs 테이블 부분)

구현 결과:

* `AuditStatus`(6개 값: `success`, `permission_denied`, `contract_error`, `guardrail_rejected`, `timeout`, `connection_closed`)를 `users.role`과 동일한 방식(`values_callable`, `validate_strings=True`, `create_constraint=False` + Alembic 명시적 `ck_audit_logs_status`)으로 구현했다.
* `id INTEGER PRIMARY KEY AUTOINCREMENT`를 SQLite DDL에 명시하도록 Migration과 ORM 테이블 옵션에 `sqlite_autoincrement=True`를 적용했다. 그 밖에 `correlation_id`/`workflow_step`(`NOT NULL` + trim 빈 값 거부 CHECK, `correlation_id`에 Index), `depth`(`CHECK(depth >= 0 AND depth <= 2)`), `is_retry`(`NOT NULL`, 기본값 `false`, Boolean CHECK), `occurred_at`(`server_default=CURRENT_TIMESTAMP`)을 구현했다.
* `UNIQUE(id, correlation_id)`를 추가해 `error_reports`의 복합 Foreign Key 부모 키로 사용할 수 있게 했다(TASK-007).
* `correlation_id`에 `UNIQUE`를 두지 않아 같은 실행에 여러 이벤트를 자유롭게 `INSERT`할 수 있고, 순서는 `id` 기준으로 재구성한다.
* `prompt`, `raw_result`, `secret` 같은 전용 필드는 추가하지 않았다. Append-Only 강제(UPDATE/DELETE 차단)는 Plan대로 구현하지 않았다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_audit_log_model.py -q`
* 결과: 통과 (13 passed) — 허용 상태값 저장(소문자 value, 6개 상태 매개변수화), 알 수 없는 상태값 DB CHECK 거부, Depth 범위(`-1`, `3`) 거부(2개 값 매개변수화), 공백 `correlation_id`/`workflow_step` 거부, `is_retry` 기본값과 Boolean CHECK 거부, 같은 `correlation_id`의 여러 이벤트가 `id` 순서대로 재구성됨. 최고 ID의 Audit 행을 삭제한 뒤 새 행을 추가해도 ID가 재사용되지 않는 회귀 테스트를 포함한다.

Plan과의 차이:

* 없음

Reviewer 의견과 처리:

* Codex 최초 검토에서 SQLAlchemy의 `autoincrement=True`만으로는 SQLite DDL에 `AUTOINCREMENT`가 생성되지 않아 최고 ID 삭제 후 ID가 재사용될 수 있음을 발견했다. Migration과 ORM에 `sqlite_autoincrement=True`를 적용하고 ID 비재사용 회귀 테스트를 추가한 뒤 재검토를 통과했다.

## `TASK-007` error_reports 모델과 복합 Foreign Key

* Status: `Completed`
* 요구사항: `FR-012`
* 실제 변경 파일:
  * `app/models/error_report.py`
  * `alembic/versions/0001_admin_db_foundation.py`(error_reports 테이블과 `audit_logs.UNIQUE(id, correlation_id)` 부분)

구현 결과:

* `ErrorReport.correlation_id`는 `NOT NULL` + trim 빈 값 거부 CHECK로 필수화했다. `audit_log_id`는 Nullable이다.
* `FOREIGN KEY (audit_log_id, correlation_id) REFERENCES audit_logs (id, correlation_id)` 복합 Foreign Key를 Migration과 ORM `__table_args__`에 동일하게 구현했다. Trigger는 만들지 않았다.
* 이 복합 FK로 (a) `audit_log_id`가 있으면 해당 이벤트가 실제로 존재하고, (b) 오류 신고와 그 이벤트의 `correlation_id`가 반드시 같으며, (c) `audit_log_id`가 `NULL`이면 특정 이벤트를 지목하지 않는 신고로 저장 가능함을 구현했다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest tests/test_error_report_model.py -q`
* 결과: 통과 (5 passed) — 공백 `correlation_id` 거부, `audit_log_id` 없는 신고 허용, 일치하는 참조 허용, 존재하지 않는 `audit_log_id` 거부, 다른 `correlation_id`를 가리키는 참조 거부(모두 복합 FK의 `IntegrityError`로 확인).

Plan과의 차이:

* 없음

Reviewer 의견과 처리:

* 미검토

## `TASK-008` 기존 테스트 격리와 문서 갱신

* Status: `Completed`
* 요구사항: `FR-013`(테스트 인프라), 문서 갱신
* 실제 변경 파일:
  * `tests/conftest.py`
  * `tests/test_health.py`
  * `tests/test_app_lifecycle.py`
  * `docs/architecture/project-structure.md`
  * `pyproject.toml`(`[tool.pytest.ini_options] pythonpath`)

구현 결과:

* `tests/conftest.py`에 `admin_db_path`(env 격리), `admin_engine`/`admin_session`(Migration이 끝난 임시 Engine/Session) Fixture를 추가해 여러 테스트 파일이 반복 없이 재사용하게 했다.
* `tests/test_health.py`의 `main_app` 테스트와 `tests/test_app_lifecycle.py`의 두 테스트가 이제 실제 Lifespan(Admin DB 준비 포함)을 실행하므로, `admin_db_path` Fixture로 `ADMIN_DB_PATH`를 `tmp_path`로 격리해 저장소의 실제 `data/admin.db`를 건드리지 않게 수정했다.
* `docs/architecture/project-structure.md`에 `alembic/`, `alembic.ini`, `data/`와 `app/db/`·`app/models/`의 실제 파일 목록·책임만 반영했다. `app/mcp/`, `app/services/`, `mcp_server/` 등 다른 절은 수정하지 않았다.
* `pyproject.toml`에 `[tool.pytest.ini_options] pythonpath = ["."]`을 추가했다(아래 "Plan과의 차이" 참고).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q`
* 결과: 통과 (51 passed, 1 warning — 기존 `httpx`/`starlette.testclient` Deprecation 경고, 이 Feature와 무관).

Plan과의 차이:

* Plan에 없던 세부 구현: `tests/conftest.py` 추가 직후 `uv run pytest`(플래그 없이)가 `ModuleNotFoundError: No module named 'app'`로 실패하는 것을 발견했다. 원인은 pytest가 `conftest.py`를 import할 때 저장소 루트가 아니라 `tests/`만 `sys.path`에 넣기 때문이며, `uv run python -m pytest`(cwd를 `sys.path`에 추가)로는 재현되지 않았다. 기존 FEAT-0001 테스트들도 동일한 잠재적 위험을 안고 있었으나 이번에 처음 `conftest.py`가 추가되며 드러났다. `pyproject.toml`에 `[tool.pytest.ini_options] pythonpath = ["."]`을 추가해 `uv run pytest` 단독 실행도 안정적으로 동작하게 했다. 이는 테스트 실행 설정일 뿐 애플리케이션 공개 경계·파일 책임에 영향이 없어 Plan을 수정하지 않고 진행했다.

Reviewer 의견과 처리:

* 미검토

## Plan 준수 및 차이

Approved Plan과 일치한 결정:

* SQLite Admin DB 분리, `Settings.admin_db_path`/`ADMIN_DB_PATH`, 기본 경로 `./data/admin.db`, `data/.gitkeep`, `.gitignore`의 `data/*.db*` 제외.
* SQLAlchemy 2.0 동기 Engine + 표준 `sqlite3` Driver, Alembic Migration, FK Pragma 활성화, `app.state` 보관, 종료 시 `dispose()`.
* Schema 준비 6단계(경로 확인 → Engine 생성 → `upgrade head` → head Revision 확인 → 4개 필수 테이블 확인 → `startup` 완료), 실패 시 `AdminDBUnavailableError` 전파로 ASGI `startup` 미완료.
* `users`(소문자 Enum value + 명시적 CHECK), `table_policies`(JSON 단일 행, DB/ORM 책임 분리), `audit_logs`(이벤트 단위 INSERT, `UNIQUE(id, correlation_id)`), `error_reports`(Trigger 없는 복합 Foreign Key) 구조.
* Repository, Service, Audit Writer, Seed 데이터, MCP·대상 DB 연결 미구현.

구현하지 못했거나 명시적으로 제외한 Plan 항목:

* 없음 — Plan에 명시된 구현 범위는 모두 완료했다.

Plan 수정·재승인이 필요했던 차이와 처리 결과:

* 차이 없음. TASK-003과 TASK-008에 기록한 두 건(Alembic `fileConfig` 미사용, `pytest` `pythonpath` 설정)은 Plan이 고정하지 않은 구현 세부(Private Helper·테스트 실행 설정) 수준의 결정이며, 공개 경계·요구사항·파일 책임을 바꾸지 않아 Plan을 수정하지 않고 진행했다.

## Feature 전체 검증

* [x] 모든 Spec 요구사항이 실제 구현과 검증에 연결됨
* [x] 모든 Plan 설계가 구현 또는 명시적으로 제외됨(제외 항목 없음)
* [x] 관련 자동 테스트 통과
* [x] 필요한 수동 검증 완료
* [x] 실행하지 못한 검증과 남은 위험 기록(아래 참고)
* [x] 필수 Codex 구현 검토 완료

## 최종 구현 검토

| Reviewer | 발견 사항 | 심각도 | 처리 Task 또는 기각 근거 | 상태 |
|---|---|---|---|---|
| Codex | `audit_logs.id`에 SQLite `AUTOINCREMENT`가 실제 적용되지 않아 최고 ID 삭제 후 재사용될 수 있음 | Medium | `TASK-006`: Migration·ORM에 `sqlite_autoincrement=True` 적용, ID 비재사용 회귀 테스트 추가 | Resolved |

## 최종 검증 기록

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 전체 자동 테스트 | `.venv\\Scripts\\python.exe -m pytest -q` | 통과 (52 passed, 1 warning) |
| 설정/빈 경로 거부 | `uv run pytest tests/test_admin_db_config.py -q` | 통과 (4 passed) |
| Lifecycle/Migration/최소 Schema 확인 | `uv run pytest tests/test_admin_db_lifecycle.py -q` | 통과 (3 passed) |
| startup 실패(경로/Schema) | `uv run pytest tests/test_admin_db_startup_failure.py -q` | 통과 (2 passed) |
| users 제약 | `uv run pytest tests/test_user_model.py -q` | 통과 (6 passed) |
| table_policies 제약 | `uv run pytest tests/test_table_policy_model.py -q` | 통과 (7 passed) |
| audit_logs 제약 | `.venv\\Scripts\\python.exe -m pytest tests/test_audit_log_model.py -q` | 통과 (13 passed) |
| error_reports 복합 FK | `uv run pytest tests/test_error_report_model.py -q` | 통과 (5 passed) |
| 수동 검증 — 기본 경로 2회 연속 기동, 데이터 보존 | `uv run python -c "..."` (실행 후 `data/admin.db` 삭제로 정리) | 통과 |
| 수동 검증 — 존재하지 않는 경로에서 startup 실패 | `ADMIN_DB_PATH=<nonexistent> uv run python -c "..."` | 통과 |
| 수동 검증 — `.gitignore` 규칙 정확성 | `git check-ignore -v data/admin.db`, `data/admin.db-journal`, `data/.gitkeep` | 통과 |
| 문서 링크 | `docs/features/0002-admin-db-foundation/` 내 상대 링크(신규 추가 없음, spec.md/plan.md 미수정 확인) | 통과 |
| 기본 포맷 | `git diff --check` (Codex 수정 파일 범위) | 통과. 저장소 전체 검사는 기존 `.gitignore`, `compose.yaml`, `mcp_tutorial/*`의 CRLF 변경 때문에 현재 WSL 환경에서 실패하며 이번 Codex 수정 파일에는 해당하지 않음 |

실행하지 못한 검증과 남은 위험:

* Docker/AWS EC2·EBS 실제 배포 환경에서의 수동 검증은 수행하지 않았다. 로컬 파일시스템의 경로 접근 실패·성공 경로만 검증했으며, 실제 EBS 마운트 환경의 동작은 이번 검증 범위 밖이다.
* `tests/test_app_lifecycle.py`, `tests/test_health.py`의 `httpx`/`starlette.testclient` Deprecation 경고는 이 Feature 이전부터 존재하던 의존성 조합 이슈이며 이번 구현에서 발생한 새로운 문제가 아니다. 수정하지 않았다(Plan 범위 밖).
* SQLite 초기 Migration 도중 프로세스가 강제 종료되는 실제 부분 초기화 상황은 재현하지 않았다(테스트는 "테이블은 있지만 `alembic_version`이 없는" 비호환 Schema 시나리오로 대체 검증했다). Plan이 이미 "전체 Schema Diff·모든 변조 조합 탐지는 만들지 않는다"고 명시했으므로 이는 알려진 범위 제한이며 새로운 위험이 아니다.
* Codex 구현 재검토에서 필수 수정 사항이 해결되었음을 확인했다. Schema 검증 예외 타입 일관화와 최근 Roadmap 개편으로 달라진 기존 Feature 문서의 Section Anchor는 FEAT-0002 구현 승인을 막지 않는 별도 문서 정합성 후속 항목이다.

## Verified 조건

* [x] 모든 필수 구현과 검증이 완료됨
* [x] Spec Acceptance Criteria와 Plan 준수 여부가 확인됨
* [x] Plan과의 차이가 해결되거나 Plan에 반영·재승인됨(중요한 차이 없음)
* [x] Codex 구현 검토 결과가 해결되거나 명시적으로 기각됨
* [x] 실제 변경, 테스트 결과와 남은 위험이 Tasks 기록과 일치함
