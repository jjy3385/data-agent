# FastAPI 실행 기반 Plan

* Feature ID: `FEAT-0001`
* Status: `Approved`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)

## 구현 목표

Spec이 정의한 "후속 Feature가 공유할 실행·설정·Lifecycle·Liveness·테스트 기반"을 저장소 루트의 독립 FastAPI 애플리케이션으로 구현한다. 이 Plan은 다음 결과를 만든다.

* 저장소 루트에서 일관된 명령으로 시작·종료할 수 있는 최소 FastAPI 애플리케이션 (FR-001, FR-003)
* 시작 전에 검증되고 유효하지 않으면 거부되는 애플리케이션 설정 (FR-002)
* 후속 Feature(MCP/DB/LLM)가 자원 초기화·정리를 이어붙일 수 있는 Application Lifespan 확장 지점 (FR-003)
* 외부 의존성을 확인하지 않는 `GET /health` Liveness Endpoint (FR-004, FR-005, NFR-001)
* 설정·시작종료·Liveness에 대한 자동 테스트 (FR-006)

MCP Server/Client Manager, Admin/대상 DB 연결, LLM Provider, RuntimeIntent/QueryPlan/SQL Guardrail, Readiness, 인증, Slack 연동, 전체 Docker Compose 구성은 이 Plan의 결과물이 아니다.

## 관련 기준과 준수 여부

* README 원칙: [절대 설계 원칙](../../../README.md#절대-설계-원칙) 중 **Fail Closed, Not Open**을 설정 검증에 적용한다 (유효하지 않은 설정이면 정상 상태인 것처럼 시작하지 않음). README는 FastAPI를 Workflow Orchestrator로 규정하지만, 이 Plan은 그 역할 중 실행 기반만 담당하고 ACL·QueryPlan·SQL Guardrail 등 Orchestrator 책임은 다루지 않는다.
* ADR: 해당 없음. ADR-0001(Read-Only DB), ADR-0002(Admin DB), ADR-0007(로컬 stdio MCP 경계)은 모두 이 Feature의 제외 범위(DB, MCP)에 속하므로 충돌하지 않는다.
* Architecture: [프로젝트 모듈 구조](../../architecture/project-structure.md)의 목표 구조(루트 `main.py`, `app/core`, `app/api`, ...)를 따른다. 단 `app/db`, `app/mcp`, `app/models`, `app/services`는 이 Plan의 범위가 아니며 후속 Feature가 채운다. [컴포넌트 책임과 경계](../../architecture/component-boundaries.md)가 정의하는 MCP Client Manager/Read-Only Query Executor 경계는 이 Plan에서 생성하지 않는다.
* Contract: 해당 없음. RuntimeIntent, QueryPlan, `execute_readonly_query`, Result Context, XAI Payload는 모두 이 Feature 범위 밖이다.

충돌하거나 변경이 필요한 기준 문서는 없다.

## 기술적 접근

* **실행/패키징**: `mcp_tutorial/`은 이 Feature의 구현 대상과 의존성에서 완전히 제외한다. 저장소 루트에 `mcp_tutorial/`과 무관한 독립 `pyproject.toml`을 두고 `uv`로 관리한다 (전용 lockfile·가상환경). 저장소에 이미 `mcp_tutorial/`이 `uv` 기반이라는 관용이 있으므로 도구 선택의 일관성을 유지하되, 의존성 파일·잠금 파일·가상환경·코드는 절대 공유하지 않는다 (NFR-002).
  * 대안으로 검토: 순수 `venv` + `requirements.txt` — 재현 가능한 잠금 파일이 없고 저장소 관용과 어긋나 기각.
  * 실행 명령: `uv run uvicorn main:app --host 0.0.0.0 --port 8000` (개발 시 `--reload` 추가). 이 명령이 FR-001이 요구하는 "일관된 시작 명령"이다. `--host`/`--port`는 배포 시점 실행 파라미터로 uvicorn CLI 인자로만 관리하며, 아래 `Settings`는 이 값을 읽거나 검증하지 않는다 (표준 실행 명령과 Settings의 책임을 분리해 불일치를 없앰 — Codex 검토 반영).
* **설정 검증**: `pydantic-settings`의 `BaseSettings`로 `APP_ENV` 환경변수만 로드한다. `app_env: Literal["local", "development", "staging", "production"] = "local"`로 기본값을 `local`로 두어 아무 환경변수 없이도 로컬 개발 시작이 가능하다. 값이 주어졌는데 허용 범위 밖이면 `ValidationError`가 `main.py` 임포트 단계에서 발생하고, Uvicorn은 소켓을 바인딩하기 전에 프로세스를 종료한다 (Fail Closed, FR-002).
  * 대안으로 검토: 런타임 첫 요청 시 지연 검증 — "정상 상태인 것처럼 시작"할 위험이 있어 Spec의 실패 시나리오와 충돌하므로 기각.
  * 대안으로 검토: `Settings`에 `app_host`/`app_port`/`log_level`을 유지하고 `main.py`가 `uvicorn.run(app, host=settings.app_host, port=settings.app_port, log_level=...)`으로 프로그래매틱 실행 — host/port/log_level까지 검증 대상으로 만들 수 있지만, 이 Feature의 어떤 FR/NFR도 host/port/log_level 검증을 요구하지 않아 범위 확장이므로 기각. 실행에 쓰이지 않는 필드를 `Settings`에 남겨두지 않는다.
* **Lifespan**: FastAPI의 `asynccontextmanager` 기반 lifespan 하나만 둔다. 현재는 시작·종료 로그만 남기는 최소 구현이며, 후속 Feature가 MCP/DB 초기화·정리 코드를 이 함수 안에 직접 추가하는 확장 지점 역할만 한다 (FR-003).
  * 대안으로 검토: 등록 가능한 startup/shutdown 콜백 레지스트리 — 현재 필요하지 않은 추상화이며 Spec의 "불필요한 추상화 회피" 제약과 충돌해 기각.
* **Liveness**: `GET /health`는 의존성 호출이 없는 순수 정적 핸들러로 구현한다. 응답 스키마를 Pydantic 모델로 고정해 `{"status": "ok"}` 이외의 값이 나갈 수 없게 한다 (FR-004, FR-005, NFR-001). Readiness Endpoint는 만들지 않는다.
* **테스트**: `pytest` + `fastapi.testclient.TestClient` (동기 방식, 내부적으로 httpx 사용). 비동기 테스트 러너 도입 없이 `TestClient`의 컨텍스트 매니저만으로 lifespan 시작·종료를 검증할 수 있어 별도 인프라가 필요 없다 (FR-006).

## 모듈과 파일 책임

| 파일 또는 모듈 | 책임 | 변경 유형 |
|---|---|---|
| `pyproject.toml` (루트) | 프로젝트 메타데이터: `requires-python = ">=3.12"`. 런타임 의존성 `fastapi>=0.115,<1.0`, `uvicorn[standard]>=0.32,<1.0`, `pydantic-settings>=2.6,<3.0`. `[dependency-groups].dev`로 테스트 전용 의존성 `pytest>=8.3,<9`, `httpx>=0.27,<1.0`(`TestClient` 구동에 필요)을 런타임 의존성과 분리 | 추가 |
| `uv.lock` (루트) | `uv lock`으로 자동 생성되는 잠금 파일. 수동 작성하지 않으며 `pyproject.toml` 변경 시 `uv lock`으로 갱신 | 추가(자동 생성) |
| `main.py` (루트) | FastAPI 앱 생성, lifespan·health 라우터 연결, ASGI entrypoint (`main:app`) | 추가 |
| `app/__init__.py` | 패키지 마커 | 추가 |
| `app/core/__init__.py` | 패키지 마커 | 추가 |
| `app/core/config.py` | `Settings`(BaseSettings) 정의, `get_settings()` 제공 | 추가 |
| `app/core/lifespan.py` | `lifespan(app)` 컨텍스트 매니저, 후속 Feature용 확장 지점, 시작·종료 로그 기록 | 추가 |
| `app/api/__init__.py` | 패키지 마커 | 추가 |
| `app/api/health.py` | `GET /health` 라우터와 `HealthResponse` 모델 | 추가 |
| `tests/test_config.py` | `Settings` 단위 테스트: 유효/유효하지 않은 `app_env` 값 검증 | 추가 |
| `tests/test_startup_failure.py` | 유효하지 않은 `APP_ENV`에서 `main` 모듈 로드·기동 자체가 실패하는지 서브프로세스로 검증 (단위 테스트와 별개의 앱 레벨 검증) | 추가 |
| `tests/test_app_lifecycle.py` | lifespan 시작·종료 코드가 실제로 실행되는지 로그 캡처로 검증 | 추가 |
| `tests/test_health.py` | `/health` 응답 검증 | 추가 |

`app/db/`, `app/mcp/`, `app/models/`, `app/services/`는 이 Plan에서 생성하지 않는다. 후속 Feature(FEAT-0002 이후)가 각자의 Spec/Plan에서 채운다.

## 공개 경계

```python
# app/core/config.py
class Settings(BaseSettings):
    app_env: Literal["local", "development", "staging", "production"] = "local"

def get_settings() -> Settings: ...

# app/core/lifespan.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]: ...

# app/api/health.py
class HealthResponse(BaseModel):
    status: Literal["ok"]

router: APIRouter  # GET /health -> HealthResponse

# main.py
app: FastAPI  # uvicorn main:app 의 ASGI entrypoint
```

Private Helper(로그 포맷, 내부 상수 등)는 이 Plan에서 고정하지 않는다.

## 동작과 데이터 흐름

1. `uv run uvicorn main:app ...`을 저장소 루트에서 실행한다.
2. `main.py` 임포트 중 `get_settings()`가 `APP_ENV` 환경변수를 읽어 `Settings`를 생성한다. 변수가 없으면 기본값 `local`을 사용한다.
   * 값이 주어졌는데 허용 범위 밖이면 `ValidationError`가 임포트 단계에서 발생 → Uvicorn이 소켓을 바인딩하기 전에 프로세스가 비정상 종료된다 (실패 시나리오 충족).
   * 값이 없거나 유효하면 `Settings` 인스턴스가 생성되고 다음 단계로 진행한다.
3. `FastAPI(lifespan=lifespan)`로 앱을 생성하고 `health.router`를 포함한다.
4. ASGI startup 이벤트에서 `lifespan`의 `yield` 이전 코드(현재는 로그만)가 실행된다 — 후속 Feature의 MCP/DB 초기화가 붙는 지점.
5. `GET /health` 요청은 의존성 호출 없이 즉시 `200 {"status": "ok"}`를 반환한다.
6. 프로세스 종료 신호(SIGINT/SIGTERM) 또는 테스트 컨텍스트 종료 시 ASGI shutdown 이벤트가 발생하고 `lifespan`의 `yield` 이후 코드(현재는 로그만)가 실행된 뒤 정상 종료한다.

상태 전이: `NOT_STARTED → 설정 검증 → (실패: 프로세스 종료) | (성공) → Lifespan 시작 → 요청 처리(Liveness) → Lifespan 종료 → STOPPED`

## 오류·보안·경계 처리

* 유효하지 않은 설정 값은 `main.py` 임포트 단계에서 예외로 전파되며, 기본값으로 대체하거나 부분적으로 시작하지 않는다 (Fail Closed).
* `/health` 핸들러는 외부 자원 호출이나 조건 분기 없는 정적 로직만 수행하므로, 핸들러가 정상적으로 호출되는 정상 실행 경로에서는 항상 `200` + `{"status": "ok"}`를 반환한다. 이 보장은 핸들러 코드 자체의 정상 경로에 한정하며, 프로세스 크래시·OOM 등 ASGI 서버 프로세스 수준 장애는 이 Feature의 오류 처리 대상이 아니다. 외부 자원을 호출하지 않으므로 이 핸들러에는 Timeout이나 연결 정리 책임이 없다.
* Lifespan은 현재 자원을 획득하지 않으므로 예외 시 정리할 대상이 없다. 후속 Feature가 자원을 추가하면 각자의 Plan에서 정리 책임과 예외 처리를 정의해야 한다.
* 인증, ACL, DB 연결 실패, MCP 호출 실패 등은 이 Feature의 범위가 아니므로 다루지 않는다 (NFR-003).

## 테스트 전략

* **단위 테스트** (`tests/test_config.py`): `Settings`에 유효한 `app_env` 값(기본값 `local` 포함)과 허용 범위 밖 값을 각각 주입해 성공/`ValidationError` 발생을 검증한다.
* **통합 테스트 — 기동 실패** (`tests/test_startup_failure.py`): `APP_ENV`를 허용되지 않는 값으로 설정한 뒤 `main` 모듈을 서브프로세스로 임포트/실행해 실제로 애플리케이션 로드·기동 자체가 실패(비정상 종료 또는 예외)하는지 검증한다. `test_config.py`의 단위 검증은 `Settings` 클래스만 확인하므로, 이 테스트로 "애플리케이션이 정상 상태인 것처럼 시작하지 않는다"는 Spec의 실패 시나리오를 앱 레벨에서 재확인한다.
* **통합 테스트 — Lifespan 실제 실행** (`tests/test_app_lifecycle.py`): `TestClient(app)`의 `__enter__()`/`__exit__()`를 명시적으로 호출해 시작과 종료 사이·이후 시점을 구분하고, 각 시점에 `caplog`로 lifespan이 남기는 시작/종료 로그 메시지가 정확히 존재하는지 검증한다. 단순히 예외가 없음을 확인하는 것과 달리 시작·종료 코드가 실제로 실행되었음을 직접 검증한다.
* **통합 테스트 — Liveness** (`tests/test_health.py`): `GET /health`가 `200` + 정확히 `{"status": "ok"}`를 반환하는지 검증한다.
* **수동 검증**: `uv run uvicorn main:app --host 0.0.0.0 --port 8000`으로 기동 후 `curl localhost:8000/health` 응답 확인, `Ctrl+C`로 정상 종료 로그 확인, 유효하지 않은 `APP_ENV` 값으로 기동 시도해 시작 전 거부되는지 확인.
* Spec Acceptance Criteria와의 연결은 아래 "요구사항 추적" 표를 따른다.

## 요구사항 추적

| Spec 요구사항 | Plan 설계 | 검증 전략 |
|---|---|---|
| `FR-001` | 루트 `pyproject.toml` + `uv run uvicorn main:app ...` 단일 시작 명령 | 수동 검증: 저장소 루트에서 명령 실행 확인 |
| `FR-002` | `app/core/config.py`의 `Settings`(`app_env`, 기본값 `local`)가 임포트 시점에 검증, 실패 시 예외 전파 | `tests/test_config.py` (Settings 단위), `tests/test_startup_failure.py` (앱 로드·기동 실패 통합) |
| `FR-003` | `app/core/lifespan.py`의 `lifespan()` 컨텍스트 매니저, 후속 Feature 확장 지점 | `tests/test_app_lifecycle.py` (시작·종료 로그 캡처로 실제 실행 검증) |
| `FR-004` | `app/api/health.py`의 `GET /health`, 의존성 호출 없음 | `tests/test_health.py` |
| `FR-005` | `HealthResponse(status: Literal["ok"])`로 응답 고정 | `tests/test_health.py` |
| `FR-006` | `tests/test_config.py`, `tests/test_startup_failure.py`, `tests/test_app_lifecycle.py`, `tests/test_health.py` 4종 자동 테스트 | `pytest` 실행 결과 |
| `NFR-001` | `/health` 핸들러가 MCP/DB/LLM을 호출하지 않는 정적 응답만 반환 | `tests/test_health.py` (응답 본문 정확히 일치 검증), 코드 리뷰 |
| `NFR-002` | `mcp_tutorial/`을 구현 대상과 의존성에서 완전히 제외, 루트에 독립된 `pyproject.toml`/코드만 생성 | 코드 리뷰: 최종 변경 파일 목록에 `mcp_tutorial/` 경로가 포함되지 않았는지 확인 |
| `NFR-003` | 인증·DB·MCP·LLM 관련 의존성·설정 필드를 포함하지 않음 | 코드 리뷰, `pyproject.toml` 의존성 목록 확인 |
| `AC` 저장소 루트에서 시작 가능 | FR-001과 동일 | 수동 검증 |
| `AC` 유효한 설정으로 정상 시작·종료 | FR-002 + FR-003 | `tests/test_app_lifecycle.py` |
| `AC` 유효하지 않은 설정은 시작 전 거부 | FR-002 | `tests/test_config.py` (단위), `tests/test_startup_failure.py` (앱 로드 실패 통합) |
| `AC` `/health` 200 + 정확히 `{"status":"ok"}` | FR-004 + FR-005 | `tests/test_health.py` |
| `AC` `/health`가 MCP/DB/LLM 준비 상태를 검사하지 않음 | NFR-001과 동일 | `tests/test_health.py`, 코드 리뷰 |
| `AC` Readiness Endpoint 미포함 | 설계상 `/ready` 등 추가 라우터를 만들지 않음 | 코드 리뷰 (라우터 목록에 없음 확인) |
| `AC` 설정·시작종료·Liveness 자동 테스트 존재 | FR-006과 동일 | `pytest` 실행 결과 |
| `AC` `mcp_tutorial/` 파일 미변경 | NFR-002와 동일 | 코드 리뷰: 최종 변경 파일 목록에 `mcp_tutorial/` 경로 없음 확인 |

## 미결정 사항

없음. 실행/패키징(uv), 설정 검증(pydantic-settings), Lifespan 확장 방식, 테스트 도구(pytest + TestClient)를 포함해 Tasks 작성에 영향을 줄 수 있는 기술 질문은 위 "기술적 접근"에서 모두 결정했다.

## 검토 기록

Codex 검토 결과와 반영 결정을 기록한다. 이 Plan은 단일 컴포넌트의 저위험 Bootstrap 범위이므로 추가 Reviewer 검토는 수행하지 않는다.

| Reviewer | 발견 사항 | 심각도 | 결정과 근거 | 상태 |
|---|---|---|---|---|
| Codex | 표준 실행 명령(`--host`/`--port`)이 `Settings`의 `app_host`/`app_port`/`log_level`과 실제로 연결되지 않는 죽은 필드였음 | Medium | `app_host`/`app_port`/`log_level`을 `Settings`에서 제거하고 `app_env`(기본값 `local`)만 유지. host/port는 uvicorn CLI 인자로만 관리 | Resolved |
| Codex | 유효하지 않은 설정 검증이 `Settings` 단위 테스트에만 그쳐 실제 애플리케이션 로드·기동 실패를 확인하지 않음 | High | `tests/test_startup_failure.py` 추가: 잘못된 `APP_ENV`로 `main` 모듈을 서브프로세스에서 임포트해 기동 실패를 검증 | Resolved |
| Codex | Lifespan 테스트가 예외 없음만 확인하고 시작·종료 코드의 실제 실행 여부는 검증하지 않음 | Medium | `tests/test_app_lifecycle.py`를 `caplog` 기반으로 변경해 시작/종료 시점 로그 메시지 존재를 직접 검증 | Resolved |
| Codex | `requires-python`, 의존성 버전 범위, 런타임/테스트 의존성 구분, `uv.lock` 생성 책임이 Plan에 없음 | Low | `pyproject.toml` 행에 `requires-python>=3.12`, 버전 범위, `[dependency-groups].dev` 분리를 명시하고 `uv.lock`을 자동 생성 파일로 파일 책임 표에 추가 | Resolved |
| Codex | `mcp_tutorial/` 변경 여부 검증이 저장소가 항상 clean하다는 가정에 의존해, 기존 미커밋 변경이 있는 경우를 다루지 못함 | Medium | 1차로 `git status --porcelain -- mcp_tutorial/` 기준선 diff 비교를 도입했으나 과도하게 복잡하다는 후속 피드백에 따라, `mcp_tutorial/`을 구현 대상·의존성에서 완전히 제외하고 최종 변경 파일 목록에 `mcp_tutorial/` 경로가 없는지 코드 리뷰로만 확인하는 방식으로 단순화 | Resolved |
| Codex | 문서 상단에 템플릿 자체의 제목·안내문이 남아 있었고, `/health` 오류 설명이 프로세스 수준 장애까지 포괄하듯 과도하게 넓게 서술됨 | Low | 템플릿 제목/안내 블록 제거. `/health` 오류 서술을 "정상 실행 경로"로 범위를 좁히고 프로세스 수준 장애는 이 Feature의 범위 밖임을 명시 | Resolved |

## Plan 승인 조건

* [x] Approved Spec의 모든 요구사항을 추적함
* [x] ADR, Architecture와 Contract에 충돌하지 않음
* [x] 공개 경계, 실패 동작과 테스트 전략이 명확함
* [x] 기술 미결정 사항이 없음
* [x] 필수 Codex 검토 의견이 해결되거나 기각 근거가 기록됨
