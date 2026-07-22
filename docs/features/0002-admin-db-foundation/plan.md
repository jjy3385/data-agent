# Admin DB 기반 Plan

* Feature ID: `FEAT-0002`
* Status: `Approved`
* Development Track: `Standard`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)

## 구현 목표

대상 AdventureWorks2022와 분리된 SQLite Admin DB 기반을 만든다. `users`, `table_policies`, `audit_logs`, `error_reports` 4개 관리 데이터 구조와 DB 제약, 반복 실행해도 기존 데이터를 보존하는 Schema 준비, 그 준비 과정과 자동 테스트(FR-001~FR-013, NFR-001~NFR-005)가 이 Plan의 결과물이다.

운영용 사용자·정책 Repository, Audit Writer, 오류 신고 Service, Workflow 통합, Seed 데이터, MCP·대상 DB 연결은 Spec의 제외 범위이며 이 Plan에서 만들지 않는다.

## 관련 기준과 준수 여부

* README **Fail Closed, Not Open**: Admin DB 경로·Schema 준비 실패 시 애플리케이션 시작을 중단한다.
* [ADR 0002 Admin Database](../../adr/0002-admin-db.md): 환경별 경로 설정, 영속 Block Storage, 단일 인스턴스, Fail Closed, 별도 접근 경계를 그대로 따른다.
* [프로젝트 모듈 구조](../../architecture/project-structure.md): `app/db/`(Admin DB 세션), `app/models/`(SQLAlchemy ORM) 책임 분리를 따른다. 이 Plan은 저장소 루트에 `alembic/`, `alembic.ini`, `data/`를 새로 추가하는데, 현재 목표 구조 다이어그램에는 아직 없다. Plan이 `Approved`된 뒤 구현 단계에서 코드와 함께 이 문서를 갱신한다(아래 "모듈과 파일 책임" 참고). Plan 작성 단계에서는 수정하지 않는다.
* [0007 Local stdio MCP DB Boundary](../../adr/0007-local-stdio-mcp-db-boundary.md): 대상 DB·MCP 실행 경계를 규정하며, 이 Plan은 그 경계에 속하는 코드를 추가하지 않으므로 충돌하지 않는다.
* Contract: 해당 없음.

충돌하거나 변경이 필요한 기준 문서는 없다.

## 기술적 접근

### 1. DB와 배포 결정

대상 AdventureWorks2022와 완전히 분리된 SQLite 파일을 Admin DB로 사용한다. 로컬 개발과 단일 EC2/EBS 데모는 동일한 코드 경로를 쓰고, `Settings.admin_db_path`(환경변수 `ADMIN_DB_PATH`, 기본값 `./data/admin.db`) 하나의 설정값만 다르다. 애플리케이션은 부모 디렉터리를 자동 생성하지 않는다 — 로컬 기본 경로는 저장소에 `data/.gitkeep`을 추가해 클론 시점부터 존재하게 하고, `.gitignore`에 `data/*.db`를 추가해 실제 DB 파일은 버전 관리에서 제외한다. 운영·EBS 경로가 마운트되지 않아 존재하지 않으면 그대로 Fail Closed한다. Admin DB 경로 접근 또는 Schema 준비가 실패하면 ASGI `startup`이 완료되지 않는다(NFR-002). 여러 FastAPI 인스턴스가 하나의 SQLite 파일을 공유하는 구성은 지원하지 않는다(NFR-003, ADR-0002).

### 2. DB 접근 기술

[프로젝트 모듈 구조](../../architecture/project-structure.md)가 `app/models/`를 SQLAlchemy ORM으로 지정하므로 SQLAlchemy 2.0을 사용한다. 표준 라이브러리 `sqlite3` Driver 기반의 동기(Sync) `Engine`으로 연결한다 — 이 Feature는 어떤 Repository나 Endpoint도 추가하지 않아 비동기 Driver(`aiosqlite`)를 정당화할 실제 호출 경로가 없고, MVP는 단일 워커·소규모 관리 데이터(ADR-0002)를 전제하므로 동기 접근으로 충분하다. Schema는 Alembic으로 관리한다(3절). `Engine`의 `connect` 이벤트에서 `PRAGMA foreign_keys=ON`을 실행해 모든 커넥션에 SQLite Foreign Key 강제를 켠다(SQLite는 연결마다 기본 비활성 상태로 시작). 준비가 끝난 `Engine`과 `sessionmaker`는 `app.state`에 보관해 후속 Feature(Repository, ACL 평가)가 이어 쓸 확장 지점으로 남기며, 이 Feature 자체는 이를 소비하는 API를 추가하지 않는다. Lifespan 종료 시 `engine.dispose()`로 커넥션 풀을 정리한다. `app/db/`는 대상 MSSQL Driver를 포함하지 않는다(NFR-001).

### 3. Schema 관리

시작 시 Schema 준비는 다음으로 제한한다.

1. Admin DB 경로(부모 디렉터리 존재·쓰기 가능) 확인
2. Engine 생성(FK Pragma 포함)
3. Alembic `upgrade head` 실행 — 애플리케이션이 이미 만든 Engine/Connection을 그대로 재사용해 Migration을 적용한다(환경마다 다른 `admin_db_path`를 그대로 반영하기 위함)
4. 현재 Revision이 코드의 head와 일치하는지 확인
5. `users`, `table_policies`, `audit_logs`, `error_reports` 4개 필수 테이블 존재 확인
6. 성공하면 `Engine`/`sessionmaker`를 `app.state`에 저장하고 ASGI `startup` 완료

1~5단계 중 하나라도 실패하면 예외가 전파되어 ASGI `startup`이 완료되지 않고, 애플리케이션은 정상 요청 처리 상태에 진입하지 않는다(NFR-002, 실패 시나리오 1). `main.py` 임포트 시점의 `Settings` 형식 검증(빈 경로 거부)과 이 목록의 1단계(실제 파일시스템 접근)는 서로 다른 시점이다.

이 Feature는 컬럼 타입 비교, CHECK SQL 문자열 비교, Unique/Index 이름 비교, Foreign Key 정의 재검사, Trigger 존재 검사, 전체 Schema Diff, 수동 DB 변조 탐지를 위한 별도 런타임 검증 시스템을 만들지 않는다. 이런 세부 제약이 Migration에 올바르게 생성되는지는 Migration·모델 테스트로 확인하며, 매 애플리케이션 시작마다 다시 검사할 대상이 아니다. 테스트는 `Engine`/`sessionmaker`와 동일한 코드 경로를 pytest `tmp_path` 기반 임시 SQLite 파일로 실행해 실제 배포와 같은 경로를 검증한다.

### 4. users

별도 `roles`/`user_roles` 테이블 없이 단일 테이블로 표현한다.

| 컬럼 | 제약 |
|---|---|
| `id` | `INTEGER PRIMARY KEY` |
| `slack_user_id` | `NOT NULL`, trim 후 빈 값 거부, `UNIQUE` |
| `is_active` | `NOT NULL`, 기본값 `true`, `0`/`1` CHECK |
| `role` | `NOT NULL`, 기본값 없음, 허용 값 CHECK |

허용 역할은 `supply_risk_analyst`, `inventory_viewer` 둘뿐이다(FR-005). Python `Enum`은 소문자 값(`.value`)으로 저장하고, ORM 대입 시점 검증과 별개로 Alembic Migration에 명시적 `CHECK (role IN ('supply_risk_analyst', 'inventory_viewer'))`를 작성해 ORM을 거치지 않는 SQL 경로도 동일하게 보호한다. `role`에 기본값을 두지 않아 값 누락은 `NOT NULL` 위반으로 거부되며, 무권한 사용자를 기본 역할로 대체하는 경로 자체가 없다(실패 시나리오 2). Seed 사용자는 만들지 않는다. 미등록·비활성 사용자를 실제로 판별하는 ACL 로직은 후속 Feature 책임이다.

### 5. table_policies

역할·물리 Schema·Table 조합의 정책 하나를 한 행으로 표현하는 JSON 단일 행 구조를 사용한다.

| 컬럼 | 제약 |
|---|---|
| `id` | `INTEGER PRIMARY KEY` |
| `role` | `users.role`과 동일한 허용 값 CHECK |
| `schema_name` / `table_name` | `NOT NULL`, trim 후 빈 값 거부 |
| `allowed_columns` | `NOT NULL`, JSON 배열(아래 제약) |
| — | `UNIQUE (role, schema_name, table_name)` — 조합당 논리적으로 하나의 정책 (FR-006) |

`allowed_columns`는 `["ProductID", "Name"]` 형태의 JSON 배열 문자열이다. **DB CHECK**는 유효한 JSON이고 JSON Array 타입이며 배열 길이가 1 이상인지까지 강제한다(빈 배열 `[]` 거부). **ORM 모델 검증**(`@validates`)은 그 안의 규칙 — 모든 원소가 문자열인지, trim 후 빈 문자열이 아닌지, `"*"` Wildcard가 아닌지, 중복이 없는지 — 을 담당한다. 두 계층의 책임은 이렇게 나뉘며, ORM 검증은 SQLAlchemy를 거치는 쓰기 경로에서만 적용된다는 것 이상으로 과장하지 않는다. DB 파일을 직접 여는 임의 변조 경로는 이 Feature가 보호하는 공개 쓰기 경계가 아니다.

정책이 없거나 컬럼이 `allowed_columns`에 없는 상태를 "허용"으로 표현할 별도 플래그나 Nullable 컬럼은 두지 않는다(FR-007). 대상 DB Schema를 조회·동기화하는 코드가 없으므로 새 컬럼은 명시적으로 추가되기 전까지 어떤 정책에도 나타나지 않는다(FR-008). 실제 ACL 평가·Metadata 교집합 계산은 이 Feature에서 구현하지 않는다.

### 6. audit_logs

이벤트 단위 단일 테이블이며 실행 요약 행을 반복 갱신하는 설계는 쓰지 않는다.

| 컬럼 | 제약 |
|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` — 이벤트 순서 재구성 키 |
| `correlation_id` | `NOT NULL`, trim 후 빈 값 거부, Index |
| `workflow_step` | `NOT NULL`, trim 후 빈 값 거부 |
| `depth` | `0` 이상 `2` 이하(README/ADR-0004의 MVP 최대 2-Depth) |
| `status` | 허용 값만 저장하는 CHECK (FR-010) |
| `is_retry` | `NOT NULL`, 기본값 `false`, `0`/`1` CHECK |
| `occurred_at` | 발생 시각 |

허용 `status` 값은 `success`, `permission_denied`, `contract_error`, `guardrail_rejected`, `timeout`, `connection_closed` 6개다. `status`(결과 종류)와 `is_retry`(재시도 시도 여부)는 서로 다른 축으로 분리한다(Spec 시나리오 4). `correlation_id`에는 `UNIQUE`를 두지 않아 같은 실행에 여러 이벤트를 자유롭게 `INSERT`할 수 있고, 후속 이벤트를 위해 기존 행을 `UPDATE`할 구조적 필요가 없다(FR-011). `occurred_at`은 표시용이며, 같은 `correlation_id`의 실제 발생 순서는 `AUTOINCREMENT`로 항상 증가하는 `id` 기준으로 재구성한다. `prompt`, `raw_result`, `secret` 같은 전용 필드는 두지 않는다(NFR-005) — Payload Allowlist·마스킹은 후속 Audit Writer 책임이다. `UPDATE`/`DELETE`를 막는 Append-Only 강제도 후속 Audit Feature 책임으로 남긴다.

### 7. error_reports

Trigger 없이 **복합 Foreign Key**로 관계를 강제한다. `audit_logs`에 `UNIQUE (id, correlation_id)`를 추가해 SQLite가 이 조합을 참조 대상으로 허용하게 하고, `error_reports`는 다음과 같다.

| 컬럼 | 제약 |
|---|---|
| `id` | `INTEGER PRIMARY KEY` |
| `correlation_id` | `NOT NULL`, trim 후 빈 값 거부 (FR-012) |
| `audit_log_id` | Nullable |
| — | `FOREIGN KEY (audit_log_id, correlation_id) REFERENCES audit_logs (id, correlation_id)` |

이 복합 Foreign Key 하나로 다음을 보장한다: `audit_log_id`가 있으면 해당 Audit 이벤트가 실제로 존재하고, 오류 신고와 그 이벤트의 `correlation_id`가 반드시 같으며, 그 일치를 깨뜨리는 `audit_logs.correlation_id` 변경은 허용되지 않는다. `audit_log_id`가 `NULL`이면 특정 이벤트를 지목하지 않는 신고로 저장할 수 있다. 오류 신고 API와 Slack 흐름은 이 Feature에서 구현하지 않는다.

## 모듈과 파일 책임

| 파일 | 책임 | 변경 |
|---|---|---|
| `app/core/config.py` | `Settings.admin_db_path` 추가 | 수정 |
| `app/core/lifespan.py` | Admin DB 준비 진입점 호출, 실패 시 예외 전파, 종료 시 정리 | 수정 |
| `app/db/errors.py` | Admin DB 준비 실패 예외 정의 | 추가 |
| `app/db/session.py` | Engine·Sessionmaker 생성, FK Pragma 등록 | 추가 |
| `app/db/schema.py` | Migration 적용과 최소 Schema 확인(3절) | 추가 |
| `app/models/base.py` | 공유 `DeclarativeBase` | 추가 |
| `app/models/user.py` | `User`/`UserRole` | 추가 |
| `app/models/table_policy.py` | `TablePolicy`와 JSON `@validates` 검증 | 추가 |
| `app/models/audit_log.py` | `AuditLog`/`AuditStatus` | 추가 |
| `app/models/error_report.py` | `ErrorReport`와 복합 FK 매핑 | 추가 |
| `alembic.ini` | Alembic 설정, `sqlalchemy.url`은 런타임에 주입 | 추가 |
| `alembic/env.py` | 모델 Metadata 연결 | 추가 |
| `alembic/versions/0001_admin_db_foundation.py` | 4개 테이블과 제약 생성 | 추가 |
| `data/.gitkeep` | 기본 경로 디렉터리를 클론 시점부터 보장 | 추가 |
| `.gitignore` | `data/*.db*` 제외 규칙 추가 | 수정 |
| `pyproject.toml` | `sqlalchemy`, `alembic` 의존성 추가 | Approved Plan 이후 구현 단계 |
| `uv.lock` | 의존성 반영 후 갱신 | Approved Plan 이후 구현 단계 |
| `tests/` (Admin DB 관련) | "테스트 전략"의 각 범주에 대응하는 자동 테스트 | 추가 |
| `docs/architecture/project-structure.md` | 목표 구조에 `alembic/`, `data/` 반영 | Approved Plan 구현 단계에서 코드와 함께 갱신 |

`app/services/`, `mcp_server/`, `app/mcp/`, `main.py`는 이 Plan에서 변경하지 않는다.

## 공개 경계

후속 코드가 실제로 사용할 대상만 고정한다. Private Helper와 구현 함수 세부는 고정하지 않는다.

* `Settings.admin_db_path: str`(기본값 `./data/admin.db`, 환경변수 `ADMIN_DB_PATH`)
* `app/db/schema.py`의 Admin DB 준비 진입점 함수 — Migration 적용과 최소 Schema 확인을 수행하고 실패 시 예외를 던진다.
* `app.state.admin_db_engine: Engine`, `app.state.admin_db_sessionmaker: sessionmaker[Session]`
* `app/models/base.py`의 `Base(DeclarativeBase)`와 `User`, `TablePolicy`, `AuditLog`, `ErrorReport` ORM 모델(필드·제약은 "기술적 접근" 참고)

## 오류·보안·경계 처리

시작 실패 동작은 "3. Schema 관리"를 따른다(중복 서술하지 않음). 데이터 계층에서는 4~7절의 CHECK/UNIQUE/Foreign Key/ORM 검증이 곧 보안 경계다 — 허용되지 않은 역할, 중복 사용자, 중복 정책, 빈/유효하지 않은 JSON 배열, 존재하지 않거나 다른 실행의 Audit 참조는 저장 시점에 거부된다(실패 시나리오 2~4). `/health`는 이 Plan에서 수정하지 않으며 계속 Admin DB를 검사하지 않는 Liveness로 남는다. Audit Append-Only 강제, Payload 마스킹, 오류 신고 API, 실제 ACL 평가, 다중 인스턴스 동시성 제어, 대상 DB·MCP 접근은 이 Feature의 범위 밖이다.

## 테스트 전략

개별 테스트 함수명은 고정하지 않고 검증 범주로만 정리한다.

* **설정**: 기본 경로, 빈 경로 거부.
* **Lifecycle**: `tmp_path` 기반 임시 DB 경로로 정상 `startup`/`shutdown`.
* **Migration**: 최초 생성, 반복 실행, 기존 데이터 보존.
* **최소 Schema 확인**: head Revision과 4개 필수 테이블.
* **users**: Slack ID Unique·공백 거부, 필수 활성 상태, 허용·거부 역할.
* **table_policies**: JSON 배열 필수(빈 배열 거부), ORM의 Wildcard·공백·중복 거부.
* **audit_logs**: 상태 값, Depth 범위, 재시도 여부, 이벤트 순서 재구성.
* **error_reports**: 없는 Audit 참조와 다른 `correlation_id` 참조 거부.
* **startup 실패**: 접근할 수 없는 경로, Migration/Schema 확인 실패 시 요청 처리에 도달하지 못함.
* **`/health` 회귀**: `tmp_path`로 `ADMIN_DB_PATH`를 격리해 저장소의 실제 `data/admin.db`를 오염시키지 않고 기존 응답을 재검증.

동일 제약을 ORM 경로와 원시 SQL 경로에서 중복 검증하거나, 의도적으로 잘못된 원시 SQL 삽입이 성공하는 것을 증명하는 테스트, CHECK 이름·SQL 문자열 비교, 테이블·Index를 하나씩 지워 모든 Drift 조합을 검증하는 테스트는 만들지 않는다. 정상 경로와 대표 실패 경로 검증으로 충분하다.

## 요구사항 추적

| 요구사항 | 설계 | 검증 |
|---|---|---|
| `FR-001` | 대상 DB와 분리된 SQLite Engine만 생성(2절) | Migration 테스트, 코드 리뷰 |
| `FR-002` | `Settings.admin_db_path` 환경변수 주입(1절) | 설정 테스트 |
| `FR-003` | Alembic 멱등 적용 + 최소 Schema 확인(3절) | Migration·최소 Schema 확인 테스트 |
| `FR-004` | `slack_user_id` UNIQUE·공백 거부, `is_active`/`role` NOT NULL(4절) | users 테스트 |
| `FR-005` | 허용 역할 CHECK, 기본값 없는 `role`(4절) | users 테스트 |
| `FR-006` | `allowed_columns` JSON + `UNIQUE(role,schema_name,table_name)`(5절) | table_policies 테스트 |
| `FR-007` | 전체 허용 플래그·Nullable 없음(5절) | table_policies 테스트, 코드 리뷰 |
| `FR-008` | 빈 배열 DB 거부 + Wildcard/중복 ORM 거부, Schema 동기화 코드 없음(5절) | table_policies 테스트 |
| `FR-009` | `correlation_id`/`workflow_step`/`depth`/`status`/`occurred_at`, `id` 기반 순서(6절) | audit_logs 테스트 |
| `FR-010` | `status` 6개 값 CHECK(6절) | audit_logs 테스트 |
| `FR-011` | `correlation_id` UNIQUE 미적용, 매 이벤트 INSERT(6절) | audit_logs 테스트 |
| `FR-012` | `correlation_id` NOT NULL, 복합 FK(7절) | error_reports 테스트 |
| `FR-013` | 아래 전 범주 자동 테스트 | `pytest` 실행 결과 |
| `NFR-001` | `app/db/`가 SQLite 전용, `mcp_server/`·`app/mcp/` 미수정 | 코드 리뷰 |
| `NFR-002` | 경로·Migration·Schema 확인 실패 시 `startup` 미완료(3절) | startup 실패 테스트 |
| `NFR-003` | 잠금·다중 프로세스 조정 코드 미추가 | 코드 리뷰 |
| `NFR-004` | 환경변수로 외부 영속 경로 주입, 부모 디렉터리 자동 생성 없음(1절) | 설정·startup 실패 테스트 |
| `NFR-005` | `audit_logs`에 secret/prompt/result 전용 필드 없음(6절) | audit_logs 테스트, 코드 리뷰 |

Spec Acceptance Criteria는 위 각 행의 설계·검증으로 충족되며 별도 표로 반복하지 않는다.

## 미결정 사항

없음.

## 검토 기록

Codex 검토는 필수다. 아래 10개 항목은 지금까지의 검토에서 발견되어 사용자가 결정을 확정한 사항이며, Plan 반영과 재검토를 완료했다.

| Reviewer | 발견 사항 → 결정 | 심각도 | 상태 |
|---|---|---|---|
| Codex | 정책 정규화 구조(`table_policy_columns`+`before_flush`)가 빈 컬럼 집합을 DB 제약만으로 강제하지 못함 → JSON 단일 행 구조로 변경 | High | Resolved |
| Codex | Alembic 실행 성공만으로는 Schema 상태를 충분히 확인하지 못함 → head Revision 일치 + 필수 테이블 4개 확인으로 보완 | High | Resolved |
| Codex | 기본 `data/admin.db` 경로 부재와 `test_health.py`의 실제 Lifespan 실행이 로컬 DB를 오염시킬 수 있음 → `data/.gitkeep` 추가, 테스트는 `tmp_path`로 격리 | Medium | Resolved |
| Codex | Enum 저장 값이 명시되지 않아 대문자 이름이 저장될 위험 → 소문자 `value` 저장과 명시적 DB CHECK로 정리 | High | Resolved |
| Codex | 일부 필수 문자열·Boolean·Depth 제약이 누락됨 → trim 빈 값 거부, `0`/`1` CHECK, Depth `0~2` 범위 명시 | Medium | Resolved |
| Codex | `alembic/`, `data/` 추가가 `project-structure.md`에 반영되지 않음 → 구현 변경 범위에 포함 | Low | Resolved |
| Codex | "Lifespan 실패 시 소켓을 바인딩하지 않는다"는 과도한 단정 → "ASGI startup 미완료"로 축소 | Medium | Resolved |
| Codex | 이전 `Spec → Plan → Tasks` 절차 표현이 남아 있음 → 현재 사후 Tasks 절차에 맞게 "Approved Plan 이후 구현 단계"로 수정 | Low | Resolved |
| Codex | `error_reports` Trigger 기반 관계 강제가 구현·검증 복잡도를 늘림 → `audit_logs UNIQUE(id, correlation_id)` + 복합 Foreign Key로 단순화 | Medium | Resolved |
| Codex | Plan 전체가 Feature 규모 대비 과도하게 상세함(반복 설명, 런타임 검증·테스트 나열) → 핵심 설계와 검증 범주 중심으로 축약 | Medium | Resolved |

## Plan 승인 조건

* [x] Source Spec에 Development Track이 있으면 해당 Track의 문서화 수준을 적용함
* [x] Approved Spec의 모든 요구사항을 추적함
* [x] ADR, Architecture와 Contract에 충돌하지 않음
* [x] 공개 경계, 실패 동작과 테스트 전략이 명확함
* [x] 기술 미결정 사항이 없음
* [x] 필수 Codex 검토 의견이 해결되거나 기각 근거가 기록됨
