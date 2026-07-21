# FastAPI 실행 기반 Tasks

* Feature ID: `FEAT-0001`
* Status: `Verified`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)
* Source Plan: [`./plan.md`](./plan.md) (`Approved`)

## 실행 원칙

* 선행 Task와 의존 순서를 지킨다.
* AI Agent에는 한 번에 하나의 검토 가능한 Task만 요청한다.
* 코드 동작과 해당 테스트 또는 재현 가능한 검증을 같은 Task에 포함한다.
* 범위 밖 리팩터링, 파일 이동과 의존성 추가를 하지 않는다.
* `mcp_tutorial/`은 이 Feature의 구현 대상과 의존성에서 완전히 제외한다. 어떤 Task도 `mcp_tutorial/`의 코드·설정·가상환경을 참조, 수정 또는 재사용하지 않는다 (Plan NFR-002 반영).

## 요구사항 Coverage

| Spec 요구사항 | Plan 절 | 구현 Task | 검증 Task |
|---|---|---|---|
| `FR-001` | 기술적 접근 — 실행/패키징 | `TASK-001`, `TASK-005` | `TASK-005` |
| `FR-002` | 기술적 접근 — 설정 검증 | `TASK-002` | `TASK-002`, `TASK-005` |
| `FR-003` | 기술적 접근 — Lifespan | `TASK-003` | `TASK-003`(단위), `TASK-005`(통합) |
| `FR-004` | 기술적 접근 — Liveness | `TASK-004` | `TASK-004`(단위), `TASK-005`(통합) |
| `FR-005` | 기술적 접근 — Liveness | `TASK-004` | `TASK-004`(단위), `TASK-005`(통합) |
| `FR-006` | 테스트 전략 | `TASK-002`, `TASK-003`, `TASK-004`, `TASK-005` | Feature 전체 검증 |
| `NFR-001` | 기술적 접근 — Liveness | `TASK-004` | `TASK-004`(단위), `TASK-005`(통합) |
| `NFR-002` | 기술적 접근 — 실행/패키징 | `TASK-001` | Feature 전체 검증(코드 리뷰) |
| `NFR-003` | 기술적 접근 — 실행/패키징 | `TASK-001` | Feature 전체 검증(코드 리뷰) |
| `AC` 저장소 루트에서 시작 가능 | 기술적 접근 — 실행/패키징 | `TASK-001`, `TASK-005` | `TASK-005` |
| `AC` 유효한 설정으로 정상 시작·종료 | 동작과 데이터 흐름 | `TASK-003`, `TASK-005` | `TASK-005` |
| `AC` 유효하지 않은 설정은 시작 전 거부 | 오류·보안·경계 처리 | `TASK-002`, `TASK-005` | `TASK-002`, `TASK-005` |
| `AC` `/health` 200 + 정확히 `{"status":"ok"}` | 공개 경계 — `HealthResponse` | `TASK-004` | `TASK-004`(단위), `TASK-005`(통합) |
| `AC` `/health`가 MCP/DB/LLM 준비 상태를 검사하지 않음 | 기술적 접근 — Liveness | `TASK-004` | `TASK-004`(단위), `TASK-005`(통합) |
| `AC` Readiness Endpoint 미포함 | 구현 목표(범위 제외) | `TASK-004`(미구현으로 충족) | Feature 전체 검증(코드 리뷰) |
| `AC` 설정·시작종료·Liveness 자동 테스트 존재 | 테스트 전략 | `TASK-002`~`TASK-005` | Feature 전체 검증 |
| `AC` `mcp_tutorial/` 파일 미변경 | 기술적 접근 — 실행/패키징 | `TASK-001` | Feature 전체 검증(코드 리뷰) |

## 작업 순서와 의존성

```text
TASK-001 (패키징)
  └─→ TASK-002 (config.py)
        ├─→ TASK-003 (lifespan.py)  ─┐
        └─→ TASK-004 (health.py)    ─┼─→ TASK-005 (main.py 조립 + 통합 테스트) → Feature 전체 검증
```

TASK-002는 TASK-001 완료 후 시작한다. TASK-003, TASK-004는 서로 독립적이며 TASK-002 완료 후 순서 상관없이 진행할 수 있지만, 한 번에 하나씩만 검토·실행한다. TASK-005는 TASK-003, TASK-004가 모두 끝난 뒤에만 시작한다.

## `TASK-001` 프로젝트 패키징 초기화

* Status: `Completed`
* 요구사항: `FR-001`(전제), `NFR-002`, `NFR-003`
* 선행 Task: 없음
* 대상 파일:
  * `pyproject.toml` (루트, 신규)
  * `uv.lock` (루트, 신규 — `uv lock`으로 자동 생성)

구현:

* 저장소 루트에 독립된 `pyproject.toml`을 새로 작성한다 (`mcp_tutorial/`의 파일·의존성·가상환경 재사용 금지는 실행 원칙 참고).
* `requires-python = ">=3.12"`를 설정한다.
* 런타임 의존성으로 `fastapi>=0.115,<1.0`, `uvicorn[standard]>=0.32,<1.0`, `pydantic-settings>=2.6,<3.0`만 추가한다.
* `[dependency-groups].dev`에 테스트 전용 의존성 `pytest>=8.3,<9`, `httpx>=0.27,<1.0`을 런타임 의존성과 분리해 추가한다.
* `uv lock`을 실행해 `uv.lock`을 생성한다.
* 인증, Admin/대상 DB, MCP, LLM 관련 의존성은 추가하지 않는다 (NFR-003).

테스트 또는 검증:

* 정상: `uv sync`가 성공적으로 완료되고, `uv run python -c "import fastapi, uvicorn, pydantic_settings"`가 예외 없이 실행된다.
* 실패 시나리오: 해당 없음 (패키징 초기화 단계이며, 애플리케이션 기동 실패 동작은 `TASK-002`, `TASK-005`에서 검증한다).

완료 조건:

* [x] 구현 범위 충족
* [x] 관련 정상·실패 테스트 통과 (정상 경로만 해당, 실패 시나리오 없음 — 위 "테스트 또는 검증" 참고)
* [x] 실제 실행 명령과 결과 기록
* [x] Spec·Plan과 차이 또는 차이 없음 기록

실행 및 검토 기록:

* 실행 명령과 결과 (2026-07-21, 저장소 루트 `C:\workspace\data-agent`, uv 0.11.30 신규 설치 후 실행):
  1. `uv lock` → `Resolved 30 packages in 1.03s` (`uv.lock` 생성됨, 종료 코드 0)
  2. `uv sync` → `.venv` 생성, `Resolved 30 packages`, `Prepared 9 packages`, `Installed 28 packages` (종료 코드 0)
  3. `uv run python -c "import fastapi, uvicorn, pydantic_settings; print('OK', fastapi.__version__, uvicorn.__version__, pydantic_settings.__version__)"` → `OK 0.139.2 0.51.0 2.14.2` (종료 코드 0)
* 결과: 3개 명령 모두 성공(종료 코드 0). 해석된 런타임/개발 의존성이 Plan의 버전 범위(`fastapi>=0.115,<1.0`, `uvicorn[standard]>=0.32,<1.0`, `pydantic-settings>=2.6,<3.0`, `pytest>=8.3,<9`, `httpx>=0.27,<1.0`) 안에 있음을 확인함. `mcp_tutorial/`에는 TASK-001 착수 전부터 존재한 사용자 변경사항이 있으며, TASK-001은 해당 경로를 구현 대상이나 의존성으로 사용하지 않고 기존 변경사항을 그대로 보존함(`NFR-002`, 관련 AC). `uv sync`가 생성한 `.venv/`에는 uv가 자동으로 `.gitignore`(`*`)를 생성해 저장소 루트 `.gitignore`를 수정하지 않고도 추적되지 않음을 확인함.
* Spec·Plan과 차이 또는 차이 없음: 차이 없음. Plan의 `requires-python`, 런타임/개발 의존성 버전 범위, `[dependency-groups].dev` 분리, `uv.lock` 자동 생성 방식을 그대로 따름. PEP 621 프로젝트 메타데이터로 필수 `name`("data-agent-backend")과 `version`("0.1.0")을 추가하고, 프로젝트 식별을 돕기 위한 선택적 `description`을 함께 추가함(런타임/개발 의존성, `requires-python`, 버전 범위에는 변경 없음).
* Reviewer 의견과 처리: Codex 검토 결과 구현 범위와 의존성 구성에는 문제가 없었으며, `mcp_tutorial/` 상태와 `description` 필수 여부에 관한 실행 기록을 실제 상태에 맞게 수정함 (Resolved).

## `TASK-002` `app/core/config.py` — 애플리케이션 설정 검증

* Status: `Completed`
* 요구사항: `FR-002`
* 선행 Task: `TASK-001`
* 대상 파일:
  * `app/__init__.py` (신규)
  * `app/core/__init__.py` (신규)
  * `app/core/config.py` (신규)
  * `tests/test_config.py` (신규)

구현:

* `app/core/config.py`에 `pydantic-settings`의 `BaseSettings`를 상속한 `Settings`를 정의한다: `app_env: Literal["local", "development", "staging", "production"] = "local"`. 환경변수는 `APP_ENV` (pydantic-settings 기본 매핑만 사용하고 별도 별칭 규칙을 추가하지 않는다).
* `get_settings() -> Settings` 함수를 제공해 `Settings()` 인스턴스를 생성해 반환한다 (Plan 공개 경계와 동일한 시그니처).
* Plan에 없는 `app_host`, `app_port`, `log_level` 등 필드는 추가하지 않는다.

테스트 또는 검증 (`tests/test_config.py`):

* 정상: `APP_ENV`를 설정하지 않고 `get_settings()` 호출 → `app_env == "local"`. `APP_ENV`를 허용된 값(`development`, `staging`, `production`)으로 각각 설정 → 해당 값으로 생성 성공.
* 실패: `APP_ENV`를 허용 목록 밖 값(예: `invalid`)으로 설정 → `Settings()` 생성 시 `pydantic.ValidationError` 발생.

완료 조건:

* [x] 구현 범위 충족
* [x] 관련 정상·실패 테스트 통과
* [x] 실제 실행 명령과 결과 기록
* [x] Spec·Plan과 차이 또는 차이 없음 기록

실행 및 검토 기록:

* 표준 테스트 명령 (저장소 루트 `C:\workspace\data-agent`): `uv run python -m pytest tests/test_config.py -v` → `collected 5 items`, 5개 모두 `PASSED` (`test_app_env_defaults_to_local`, `test_app_env_accepts_allowed_values[development|staging|production]`(3건), `test_app_env_rejects_invalid_value`), `5 passed in 0.30s`.
* 참고: 최초 `uv run pytest tests/test_config.py -v`(콘솔 스크립트 직접 실행)는 저장소 루트가 `sys.path`에 포함되지 않아 `ModuleNotFoundError: No module named 'app'`로 실패했음. `uv run python -m pytest ...`로 실행하면 저장소 루트가 자동으로 `sys.path`에 포함되어 해결되므로, 이를 표준 명령으로 채택함.
* 결과: monkeypatch로 `APP_ENV`를 격리한 상태에서 기본값(`local`), 허용값(`development`/`staging`/`production`), 허용 목록 밖 값(`invalid` → `pydantic.ValidationError`)을 모두 확인함. `app/`, `tests/`에 `main.py`, `lifespan.py`, `health.py`는 생성하지 않음.
* Spec·Plan과 차이 또는 차이 없음: 구현(Settings 필드·기본값·`get_settings()` 시그니처·테스트 케이스)은 Plan/Task 기술과 정확히 일치하며 캐시나 추가 필드를 넣지 않음. 표준 테스트 실행 명령을 `uv run pytest ...`에서 `uv run python -m pytest ...`로 통일한 것 외에 코드·설정 변경은 없음.
* Reviewer 의견과 처리: Codex 검토 결과 문제 없음 (Approved)

## `TASK-003` `app/core/lifespan.py` — Application Lifespan 확장 지점

* Status: `Completed`
* 요구사항: `FR-003`
* 선행 Task: `TASK-002`
* 대상 파일:
  * `app/core/lifespan.py` (신규)
  * `tests/test_app_lifecycle.py` (신규)

구현:

* `app/core/lifespan.py`에 `@asynccontextmanager async def lifespan(app: FastAPI) -> AsyncIterator[None]`을 구현한다.
* `yield` 이전에 시작 로그 1회, `yield` 이후에 종료 로그 1회만 남긴다. 현재는 MCP/DB 등 실제 자원 초기화를 하지 않으며, 후속 Feature가 이 함수 본문에 직접 코드를 추가하는 확장 지점으로만 존재한다.
* 콜백 레지스트리 등 추가 추상화를 만들지 않는다 (Plan에서 검토 후 기각한 대안).

테스트 또는 검증 (`tests/test_app_lifecycle.py`):

* 이 `lifespan`만 연결한 최소 `FastAPI(lifespan=lifespan)` 테스트 앱을 구성해 독립적으로 검증한다.
* 정상: `TestClient(test_app)`의 `__enter__()` 호출 후 `caplog`에 시작 로그 메시지가 존재하는지 확인하고, 이어서 `__exit__()` 호출 후 종료 로그 메시지가 추가로 존재하는지 확인한다 (예외 없이 완료, 로그로 실제 실행을 직접 검증).
* 실패 시나리오: 해당 없음 (현재 `lifespan`은 자원을 획득하지 않으므로 실패 경로가 없다 — Plan 오류·보안·경계 처리와 일치).
* 이 파일은 `TASK-005`에서 실제 `main.app`을 대상으로 한 통합 테스트 케이스가 추가되며, 이 Task에서는 `lifespan`만 분리한 단위 검증만 다룬다.

완료 조건:

* [x] 구현 범위 충족
* [x] 관련 정상·실패 테스트 통과 (정상 경로만 해당, 실패 시나리오 없음 — 위 "테스트 또는 검증" 참고)
* [x] 실제 실행 명령과 결과 기록
* [x] Spec·Plan과 차이 또는 차이 없음 기록

실행 및 검토 기록:

* 실행 명령과 결과 (저장소 루트 `C:\workspace\data-agent`):
  1. `uv run python -m pytest tests/test_app_lifecycle.py -v` → `collected 1 item`, `test_lifespan_logs_startup_and_shutdown_exactly_once` `PASSED`, `1 passed, 1 warning in 1.15s`
  2. `uv run python -m pytest tests/test_config.py tests/test_app_lifecycle.py -v`(회귀) → `collected 6 items`, 6개 모두 `PASSED`, `6 passed, 1 warning in 0.84s`
* 결과: `lifespan`만 연결한 최소 `FastAPI(lifespan=lifespan)` 테스트 앱에 대해 `TestClient`의 `with` 블록으로 실제 Lifespan을 시작·종료함. `caplog.at_level(logging.INFO, logger="app.core.lifespan")`로 `with` 진입 직후 시작 로그(`Application startup`)가 정확히 1회, 종료 로그(`Application shutdown`)는 0회임을 확인했고, `with` 종료 후에는 시작 로그 1회·종료 로그 1회로 정확히 유지됨을 확인함(로그 실제 실행 검증). `TestClient`는 중첩 `with` 블록으로 열어 assertion 실패 시에도 정리되도록 함. 두 실행 모두 경고(warning)는 `fastapi.testclient`가 사용하는 `httpx`/`starlette.testclient` 조합에 대한 `StarletteDeprecationWarning`(설치된 `fastapi`/`starlette` 버전 조합에서 발생, 이번 구현과 무관, 의존성 변경 범위 밖이라 조치하지 않음)뿐이며 실패는 없음. `app/api`, `health.py`, `main.py`는 생성하지 않음.
* Spec·Plan과 차이 또는 차이 없음: 차이 없음. `app/core/lifespan.py`는 Plan 공개 경계(`lifespan(app: FastAPI) -> AsyncIterator[None]`)와 정확히 일치하며, `logging.getLogger(__name__)` 모듈 로거로 시작 로그(INFO, `yield` 이전 1회)와 종료 로그(INFO, `try/finally`로 `yield` 이후 1회)만 남기고 MCP/DB/LLM 등 실제 자원 초기화·정리나 콜백 레지스트리 등 추가 추상화는 넣지 않음.
* Reviewer 의견과 처리: Codex 검토 결과 문제 없음 (Approved)

## `TASK-004` `app/api/health.py` — Liveness Endpoint

* Status: `Completed`
* 요구사항: `FR-004`, `FR-005`, `NFR-001`
* 선행 Task: `TASK-002`
* 대상 파일:
  * `app/api/__init__.py` (신규)
  * `app/api/health.py` (신규)
  * `tests/test_health.py` (신규)

구현:

* `app/api/health.py`에 `HealthResponse(BaseModel)` (`status: Literal["ok"]`)를 정의한다.
* `APIRouter`에 `GET /health`를 등록하고, 핸들러는 외부 자원 호출이나 조건 분기 없이 즉시 `HealthResponse(status="ok")`를 반환한다.
* MCP, DB, LLM 준비 상태를 확인하는 코드를 추가하지 않는다 (`NFR-001`). `/ready` 등 Readiness Endpoint를 추가하지 않는다.

테스트 또는 검증 (`tests/test_health.py`):

* `health.router`만 포함한 최소 `FastAPI()` 테스트 앱을 구성해 독립적으로 검증한다.
* 정상: `GET /health` 호출 → `status_code == 200`, 응답 본문이 정확히 `{"status": "ok"}` (추가 필드 없음).
* 실패 시나리오: 해당 없음 (정적 핸들러이므로 Plan 오류 처리 절과 일치, 프로세스 수준 장애는 이 Feature의 범위 밖).
* 이 파일은 `TASK-005`에서 실제 `main.app`을 대상으로 한 통합 테스트 케이스가 추가되며, 이 Task에서는 라우터만 분리한 단위 검증만 다룬다.

완료 조건:

* [x] 구현 범위 충족
* [x] 관련 정상·실패 테스트 통과 (정상 경로만 해당, 실패 시나리오 없음 — 위 "테스트 또는 검증" 참고)
* [x] 실제 실행 명령과 결과 기록
* [x] Spec·Plan과 차이 또는 차이 없음 기록

실행 및 검토 기록:

* 실행 명령과 결과 (저장소 루트 `C:\workspace\data-agent`):
  1. `uv run python -m pytest tests/test_health.py -v` → `collected 1 item`, `test_health_returns_200_and_exact_ok_body` `PASSED`, `1 passed, 1 warning in 1.12s`
  2. `uv run python -m pytest tests/test_config.py tests/test_app_lifecycle.py tests/test_health.py -v`(회귀) → `collected 7 items`, 7개 모두 `PASSED`, `7 passed, 1 warning in 0.69s`
* 결과: `health.router`만 포함한 최소 `FastAPI()` 테스트 앱으로 `GET /health` 호출 → `status_code == 200`, 응답 본문이 정확히 `{"status": "ok"}`임을 확인함. 두 실행 모두 이전 Task부터 있던 `StarletteDeprecationWarning`(httpx→httpx2 권고, 이번 구현과 무관) 1건 외 실패는 없음. `main.py`는 생성·연결하지 않았고, `/ready` 등 Readiness Endpoint도 추가하지 않음.
* Spec·Plan과 차이 또는 차이 없음: 차이 없음. `app/api/health.py`는 Plan 공개 경계(`HealthResponse(status: Literal["ok"])`, `router: APIRouter`)와 정확히 일치하며, 핸들러는 외부 자원 호출이나 조건 분기 없이 즉시 고정 응답만 반환함 (`NFR-001`).
* Reviewer 의견과 처리: Codex 검토 결과 문제 없음 (Approved)

## `TASK-005` `main.py` 조립과 기동 실패 통합 검증

* Status: `Completed`
* 요구사항: `FR-001`, `FR-002`(앱 레벨 재확인), `FR-003`(통합 검증), `FR-004`, `FR-005`, `FR-006`, `NFR-001`(통합 검증)
* 선행 Task: `TASK-002`, `TASK-003`, `TASK-004`
* 대상 파일:
  * `main.py` (루트, 신규)
  * `tests/test_startup_failure.py` (신규)
  * `tests/test_app_lifecycle.py` (`TASK-003`에서 생성된 기존 파일에 통합 테스트 케이스 추가)
  * `tests/test_health.py` (`TASK-004`에서 생성된 기존 파일에 통합 테스트 케이스 추가)

구현:

* `main.py` 모듈 최상단에서 `get_settings()`를 호출해 `Settings`를 생성한다 (임포트 시점 검증, 실패 시 예외가 임포트 단계에서 전파됨).
* `FastAPI(lifespan=lifespan)`로 `app`을 생성하고 `app.include_router(health.router)`로 `/health`를 연결한다.
* `app`을 모듈 최상위에 노출해 `uv run uvicorn main:app ...`의 ASGI entrypoint로 사용한다.
* `main.py`에는 `Settings`/`lifespan`/`health` 조립 외의 로직(추가 라우팅, 미들웨어 등)을 넣지 않는다.

테스트 또는 검증:

* 통합 테스트 — Lifespan (`tests/test_app_lifecycle.py`에 케이스 추가): `TASK-003`의 분리된 `lifespan` 단위 테스트와 별개로, 실제 `main.app`을 대상으로 `TestClient(main.app)`의 `__enter__()`/`__exit__()`를 명시적으로 호출해 `caplog`로 시작·종료 로그가 실제로 실행되는지 검증한다. 새 테스트 파일을 만들지 않고 기존 파일에 함수를 추가한다.
* 통합 테스트 — Liveness (`tests/test_health.py`에 케이스 추가): `TASK-004`의 분리된 라우터 단위 테스트와 별개로, 실제 `main.app`에 대해 `TestClient(main.app).get("/health")`를 호출해 `200` + 정확히 `{"status": "ok"}`가 반환되는지 검증한다. 새 테스트 파일을 만들지 않고 기존 파일에 함수를 추가한다.
* 실패 자동 테스트 (`tests/test_startup_failure.py`): `APP_ENV`를 허용 목록 밖 값(예: `invalid`)으로 설정한 뒤 서브프로세스에서 `main` 모듈을 임포트/실행해 0이 아닌 종료 코드 또는 예외로 실패하는지 검증한다. 이어서 서브프로세스의 표준 오류 출력(stderr)에 문제가 된 설정 필드명(`app_env`)과 pydantic 검증 오류임을 식별할 수 있는 문자열(예: `ValidationError`)이 포함되는지 확인해, 실패 원인이 설정 검증임을 오류 출력만으로 구분할 수 있는지 검증한다. 동일한 서브프로세스 방식으로 `APP_ENV` 미설정(기본값 `local`) 또는 허용된 값일 때는 정상 임포트(종료 코드 `0`)되는지도 함께 확인한다.
* 수동 검증: 저장소 루트에서 `uv run uvicorn main:app --host 0.0.0.0 --port 8000` 실행 → `curl http://localhost:8000/health` 호출 시 `200` + `{"status":"ok"}` 확인 → `Ctrl+C`로 예외 없이 종료되는지 확인.

완료 조건:

* [x] 구현 범위 충족
* [x] `tests/test_app_lifecycle.py`, `tests/test_health.py`에 추가된 실제 `main.app` 통합 테스트 케이스 통과
* [x] `tests/test_startup_failure.py`가 실패/성공 종료 코드뿐 아니라 stderr에서 `app_env`와 검증 오류(`ValidationError`) 식별 가능함을 확인
* [x] 실제 실행 명령과 결과 기록
* [x] Spec·Plan과 차이 또는 차이 없음 기록

실행 및 검토 기록:

* 자동 테스트 실행 명령과 결과 (저장소 루트 `C:\workspace\data-agent`):
  1. `uv run python -m pytest tests/test_startup_failure.py -v` → `collected 3 items`, 3개 모두 `PASSED` (`test_invalid_app_env_fails_to_import_main_with_identifiable_error`, `test_missing_app_env_imports_main_successfully`, `test_allowed_app_env_imports_main_successfully`), `3 passed in 2.91s`
  2. `uv run python -m pytest tests/test_app_lifecycle.py tests/test_health.py -v` → `collected 4 items`, 4개 모두 `PASSED` (기존 단위 테스트 2개 + 이번에 추가한 실제 `main.app` 통합 테스트 2개), `4 passed, 1 warning in 0.83s`
  3. `uv run python -m pytest` (전체) → `collected 12 items`, 12개 모두 `PASSED`, `12 passed, 1 warning in 3.32s`
* `test_invalid_app_env_fails_to_import_main_with_identifiable_error`는 `APP_ENV=invalid`로 서브프로세스에서 `import main`을 실행해 0이 아닌 종료 코드를 확인하고, `stderr`에 `app_env`와 `ValidationError` 문자열이 모두 포함됨을 확인함(오류 원인 식별 가능성 검증).
* 수동 검증: `uv run uvicorn main:app --host 0.0.0.0 --port 8000`과 동일한 실행(venv `python -m uvicorn main:app --host 0.0.0.0 --port 8000`, 별도 콘솔 프로세스 그룹)을 스크립트로 구동해 재현 가능하게 수행함 — ① 서버가 `Application startup complete.`까지 정상 기동, ② `GET http://127.0.0.1:8000/health` 호출 시 `HTTP 200`과 정확히 `{"status":"ok"}` 확인, ③ `CTRL_BREAK_EVENT`(Windows 콘솔의 `Ctrl+C`에 대응하는 신호)를 보낸 뒤 `Shutting down` → `Waiting for application shutdown.` → `Application shutdown complete.` → `Finished server process`까지 예외 없이 완료됨을 실제 서버 로그로 확인함(그레이스풀 종료).
* 참고: 위 수동 검증에서 uvicorn 자체 로그(`Started server process`, `Application startup complete.`, `Shutting down` 등)는 콘솔에 출력되지만, `app/core/lifespan.py`가 남기는 `Application startup`/`Application shutdown` 커스텀 로그는 `main.py`에 별도 로깅 설정(`logging.basicConfig` 등)을 추가하지 않았기 때문에(Plan에서 `main.py`에 Settings/lifespan/health 조립 외 로직 추가를 금지) 콘솔에는 보이지 않음. 해당 로그가 정확히 1회씩 실행된다는 사실 자체는 `tests/test_app_lifecycle.py`의 `caplog` 기반 자동 테스트로 이미 확인되어 있으므로 기능적으로는 검증됨. 이 관찰은 Plan 위반이 아니며 수정하지 않음.
* Spec·Plan과 차이 또는 차이 없음: 차이 없음. `main.py`는 Plan이 명시한 대로 `get_settings()` 임포트 시점 호출, `FastAPI(lifespan=lifespan)`, `app.include_router(health.router)`, 모듈 최상위 `app` 노출 외의 로직을 포함하지 않음. `tests/test_app_lifecycle.py`, `tests/test_health.py`에는 기존 단위 테스트를 유지한 채 실제 `main.app` 통합 테스트만 추가했고 새 테스트 파일은 만들지 않음.
* Reviewer 의견과 처리: Codex 최종 구현 검토 결과 `TASK-005`와 `FEAT-0001` 구현 전반에 코드 결함이나 차단 사항 없음. `main.py` 조립, 설정 Fail Closed, lifespan 통합, `/health` 통합, 서브프로세스 실패 검증이 Spec·Plan과 일치함 (Approved)

## Feature 전체 검증

* [x] 모든 Spec 요구사항이 완료된 Task에 연결됨 (`FR-001`~`FR-006`, `NFR-001`~`NFR-003`, AC 8개 전부 `TASK-001`~`TASK-005`로 추적됨)
* [x] 모든 Plan 설계가 구현 또는 명시적으로 제외됨 (`app/db`, `app/mcp`, `app/models`, `app/services`는 이 Feature에서 의도적으로 미구현)
* [x] 전체 자동 테스트 통과 (`uv run python -m pytest` — `test_config.py`, `test_app_lifecycle.py`, `test_health.py`, `test_startup_failure.py`, 12개 전부 `PASSED`)
* [x] 필요한 수동 검증 완료 (`TASK-005`의 수동 검증 항목 — `/health` 200 + 정확한 본문, 그레이스풀 종료 로그 시퀀스까지 확인. 세부 사항과 관찰된 제약은 아래 "실행하지 못한 검증과 남은 위험" 참고)
* [x] 코드 리뷰: 최종 변경 파일 목록에 `mcp_tutorial/` 경로가 포함되지 않음 — `mcp_tutorial/`은 `FEAT-0001` 착수 이전부터 존재한 사용자 작성 코드이며, `FEAT-0001`은 이를 구현 대상·의존성으로 사용하거나 추가로 수정하지 않고 그대로 보존함 (`NFR-002`, 관련 AC)
* [x] 코드 리뷰: 의존성 목록에 인증·DB·MCP·LLM 관련 항목이 없음 (`pyproject.toml`에 `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `pytest`, `httpx`만 존재) (`NFR-003`)
* [x] 코드 리뷰: 라우터 목록에 `/ready` 등 Readiness Endpoint가 없음 (`main.py`/`app/api/health.py`에 `/health` 라우트만 존재) (관련 AC)
* [x] 실행하지 못한 검증과 남은 위험 기록 (아래 참고)
* [x] 필수 Codex 구현 검토 완료 (Codex 최종 구현 검토 결과 코드 결함·차단 사항 없음, `FEAT-0001` 구현 Approved — 위 "최종 구현 검토" 표 참고)

## 최종 구현 검토

| Reviewer | 발견 사항 | 심각도 | 처리 Task 또는 기각 근거 | 상태 |
|---|---|---|---|---|
| Codex | `TASK-005`가 실제 `main.app`으로 Lifespan·`/health`를 자동 통합 검증하지 않고 수동 검증에만 의존함 | High | `tests/test_app_lifecycle.py`, `tests/test_health.py`(각각 `TASK-003`, `TASK-004`에서 생성)에 `main.app` 기반 통합 테스트 케이스를 `TASK-005`에서 추가하도록 대상 파일·테스트 전략 갱신. 새 테스트 파일은 만들지 않음 | Resolved |
| Codex | `TASK-003`, `TASK-004`의 선행 Task가 `TASK-001`로 되어 있어 작업 순서 다이어그램·독립성 설명과 실제 의존 관계(설정 기반 여부)가 어긋남 | Medium | `TASK-003`, `TASK-004`의 선행 Task를 `TASK-002`로 변경하고, 작업 순서 다이어그램과 독립성 설명 문장을 일치시킴 | Resolved |
| Codex | 잘못된 `APP_ENV` 서브프로세스 테스트가 실패 여부(종료 코드)만 확인하고 오류 원인 식별 가능성은 검증하지 않음 | Medium | `TASK-005` 테스트 전략과 완료 조건에 stderr에서 설정 필드명(`app_env`)과 `ValidationError` 식별 가능 여부를 확인하는 항목 추가 | Resolved |
| Codex | `mcp_tutorial/` 관련 문구가 실행 원칙, Coverage, `TASK-001` 구현, Feature 전체 검증, 최종 검증 기록에 중복 서술됨 | Low | 실행 원칙·Coverage·Feature 전체 검증에만 필요한 서술을 남기고, `TASK-001` 구현 문구를 간결화하고 최종 검증 기록의 중복 행을 제거 | Resolved |
| Codex | `FEAT-0001`(`TASK-001`~`TASK-005`) 최종 구현 검토: 코드 결함이나 차단 사항 없음. `main.py` 조립, 설정 Fail Closed, lifespan 통합, `/health` 통합, 서브프로세스 실패 검증이 Spec·Plan과 일치함 | - | 최종 구현 결과 Approved | Approved |

고위험 구현에서 추가 Reviewer를 사용하는 경우 위 표에 행을 추가한다.

## 최종 검증 기록

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 전체 자동 테스트 | `uv run python -m pytest` | 통과 — `12 passed, 1 warning in 3.32s` |
| 기동 실패 검증 | `tests/test_startup_failure.py` (서브프로세스 기반) | 통과 — `3 passed`, 실패 케이스는 종료 코드뿐 아니라 stderr의 `app_env`/`ValidationError` 문자열까지 확인 |
| 수동 기동·Liveness·종료 검증 | `uv run uvicorn main:app --host 0.0.0.0 --port 8000`과 동일한 실행(venv `python -m uvicorn`)을 재현 가능한 스크립트로 구동 + `GET /health` + `Ctrl+C`에 대응하는 `CTRL_BREAK_EVENT` | 통과 — `HTTP 200` + 정확히 `{"status":"ok"}`, `Shutting down` → `Application shutdown complete.` → `Finished server process`까지 예외 없이 완료 |
| 문서 링크 | 저장소 내부 상대 링크 검사 | 통과 — `tasks.md`의 `Source Spec: ./spec.md`, `Source Plan: ./plan.md`가 가리키는 `docs/features/0001-fastapi-bootstrap/spec.md`, `docs/features/0001-fastapi-bootstrap/plan.md` 파일이 실제로 존재함을 확인 |
| 기본 포맷 | FEAT-0001 대상 파일 공백 검사 | 통과 — 공백 오류 없음. 기존 사용자 변경 파일에서 환경별 CRLF 감지 차이가 있으나 Feature 구현 범위 밖 |

실행하지 못한 검증과 남은 위험:

* 수동 검증은 실제 터미널에서의 `Ctrl+C` 대신, 별도 프로세스 그룹으로 띄운 동일한 서버에 Windows `CTRL_BREAK_EVENT`(콘솔 인터럽트 신호)를 보내는 재현 가능한 스크립트로 수행했다. uvicorn 자체 종료 로그(`Shutting down` 등)가 예외 없이 끝까지 출력되어 그레이스풀 종료로 판단하지만, 완전히 동일한 상호작용형 터미널 Ctrl+C 입력 자체를 재현한 것은 아니다.
* 같은 수동 검증에서 `app/core/lifespan.py`가 남기는 `Application startup`/`Application shutdown` 커스텀 로그는 콘솔에 출력되지 않았다(루트 로깅 설정 미구성 — Plan이 `main.py`에 Settings/lifespan/health 조립 외 로직 추가를 금지하므로 의도된 상태). 해당 로그가 정확히 1회씩 실행된다는 사실은 `tests/test_app_lifecycle.py`의 `caplog` 기반 자동 테스트로 이미 확인되어 있다.
* TASK-002부터 이어진 패키징 특성(콘솔 스크립트 `pytest`가 아니라 `python -m pytest`/`python -m uvicorn`처럼 저장소 루트를 `sys.path`에 포함하는 실행 방식이 필요함)은 표준 명령 채택으로 해결되어 더 이상 위험으로 기록하지 않는다.
