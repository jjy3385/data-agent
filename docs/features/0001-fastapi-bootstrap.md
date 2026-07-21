# FastAPI 실행 기반 (FastAPI Bootstrap)

> 이 문서는 프로젝트의 첫 구현 단위로서 실행 가능한 최소 FastAPI 애플리케이션, 설정 로딩 기반, 비어 있는 Lifespan과 Liveness 확인을 정의한다. MCP, DB, LLM과 업무 Workflow는 이 Feature에 포함하지 않는다.

* Feature ID: `FEAT-0001`
* 상태: `Draft`
* 관련 Roadmap 항목: [Week 1 - FastAPI 프로젝트 기본 구조](../mvp/roadmap.md#week-1-business-metadata--security-foundation)

## 목적

후속 Feature가 공통으로 사용할 루트 Python 프로젝트와 FastAPI 실행·테스트 기반을 만든다. 구현 후 개발자는 `uv`로 애플리케이션을 시작하고 `/health`를 호출하며 자동 테스트를 실행할 수 있어야 한다.

## 선행 조건과 의존성

* Python 3.13 이상과 `uv`를 로컬에서 사용할 수 있어야 한다.
* 루트 프로젝트는 `mcp_tutorial/`의 가상환경과 패키지 설정을 재사용하지 않는 독립 Python Package로 구성한다.
* Runtime에는 FastAPI, Uvicorn과 Pydantic Settings가 필요하다.
* 테스트에는 Pytest와 FastAPI TestClient가 사용하는 HTTP Client가 필요하다.
* 정확한 의존성 Version 범위는 이 문서를 `Approved`로 변경하기 전에 확정한다.

## 범위

포함:

* 루트 `pyproject.toml`과 `uv` 기반 의존성·테스트 실행 기반
* `app` Python Package 기본 구조
* FastAPI Application Factory와 루트 ASGI Application
* 환경변수 기반 최소 설정 로딩과 유효성 검사
* 후속 MCP Lifecycle을 연결할 수 있는 비어 있는 FastAPI Lifespan
* 외부 의존성을 확인하지 않는 `GET /health` Liveness Endpoint
* 설정, 애플리케이션 시작·종료와 `/health`의 자동 테스트

제외:

* `/ready` Readiness Endpoint와 외부 의존성 준비 상태 검사
* MCP Server 실행과 MCP Client Manager
* Admin DB와 대상 DB 연결
* LLM Provider
* RuntimeIntent, QueryPlan과 SQL Guardrail
* Slack 연동
* Docker Compose 전체 애플리케이션 구성
* 인증, 권한과 업무 API

## 관련 기준 문서

* Architecture: [프로젝트 모듈 구조](../architecture/project-structure.md)
* Architecture: [컴포넌트 책임과 경계](../architecture/component-boundaries.md)
* MVP Scope: [MVP 범위와 대표 시나리오](../mvp/scope.md)
* Acceptance Criteria: [MVP 완료 기준](../mvp/acceptance-criteria.md)
* 개발 절차: [AI-Assisted Development Protocol](../development-protocol.md)

이 Feature는 대상 DB 실행 경계를 구현하지 않으므로 새로운 ADR 또는 Tool Contract를 만들지 않는다.

## 관찰 가능한 동작

### 정상 동작

1. 루트에서 `uv` 명령으로 의존성을 설치하고 테스트를 실행할 수 있다.
2. ASGI Server가 루트 `main:app`을 로드하고 FastAPI Lifespan에 진입한다.
3. 지원되는 환경 설정은 `AppSettings`로 검증되어 `app.state.settings`에서 조회할 수 있다.
4. `GET /health`는 HTTP 200과 정확히 `{ "status": "ok" }`를 반환한다.
5. 애플리케이션 종료 시 Lifespan이 오류 없이 끝난다.

### 실패 동작

* 지원하지 않는 실행 환경 값은 설정 검증 오류로 거부하고 애플리케이션을 유효한 상태처럼 시작하지 않는다.
* 알 수 없는 경로는 FastAPI 기본 HTTP 404를 반환한다.
* `/health`는 아직 존재하지 않는 MCP, DB 또는 LLM 상태를 성공으로 가장하지 않는다. 이 Endpoint는 프로세스 Liveness만 나타낸다.

## 공개 경계

아래 이름과 입출력은 `Approved` 상태에서 구현 기준으로 사용한다. 내부 Helper와 파일 내부 구현은 고정하지 않는다.

```python
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    app_name: str
    environment: Literal["local", "test", "production"]


def get_settings() -> AppSettings: ...


class HealthResponse(BaseModel):
    status: Literal["ok"]


async def health() -> HealthResponse: ...


async def lifespan(app: FastAPI) -> AsyncIterator[None]: ...


def create_app(settings: AppSettings | None = None) -> FastAPI: ...
```

루트 `main.py`는 ASGI Server가 가져갈 수 있는 `app: FastAPI`를 노출한다. `create_app()`은 전달된 설정이 없으면 `get_settings()`를 사용하고 선택된 설정을 `app.state.settings`에 저장한다.

## 구현 대상

예상 추가 파일:

* `pyproject.toml`: 루트 Python Project Metadata, Runtime과 Test Dependency
* `uv.lock`: 재현 가능한 의존성 잠금 파일
* `app/__init__.py`: Application Package
* `app/core/__init__.py`: Core Package
* `app/core/config.py`: `AppSettings`와 `get_settings`
* `app/api/__init__.py`: API Package
* `app/api/health.py`: `/health` Router와 Response Model
* `main.py`: Application Factory, Lifespan과 ASGI `app`
* `tests/core/test_config.py`: 설정 정상·실패 검증
* `tests/api/test_health.py`: 시작·종료와 Liveness Contract 검증

새 외부 의존성은 FastAPI 실행, 환경변수 검증과 자동 테스트에 필요한 최소 Package로 제한한다. `mcp_tutorial/` 파일과 의존성은 수정하지 않는다.

## 구현 Task

* [ ] Task 1: 루트 `pyproject.toml`, Package와 Pytest 기반을 추가하고 `uv sync` 및 `uv run pytest --version`으로 개발 환경을 검증한다.
* [ ] Task 2: `AppSettings`와 `get_settings()`를 구현하고 기본값·환경변수 Override·지원하지 않는 환경 값 테스트를 함께 작성한다.
* [ ] Task 3: `create_app()`, 비어 있는 Lifespan과 루트 `app`을 구현하고 TestClient가 Startup·Shutdown Context에 정상 진입하는 테스트를 함께 작성한다.
* [ ] Task 4: `GET /health`와 `HealthResponse`를 구현하고 Status Code·정확한 JSON Contract·알 수 없는 경로 테스트를 함께 작성한다.
* [ ] Task 5: 전체 테스트, ASGI Import와 수동 `/health` 호출을 검증하고 이 문서의 검증 기록을 갱신한다.

## 테스트와 완료 조건

* [ ] 루트에서 `uv sync`가 성공한다.
* [ ] 루트에서 전체 Pytest Suite가 통과한다.
* [ ] 기본 설정과 환경변수 Override가 검증된다.
* [ ] 지원하지 않는 실행 환경 값이 거부된다.
* [ ] Application Startup과 Shutdown이 검증된다.
* [ ] `/health`가 HTTP 200과 정확한 Response Contract를 반환한다.
* [ ] `/health`가 MCP, DB 또는 LLM 준비 상태를 검사하지 않는다.
* [ ] `/ready`가 이 Feature에 추가되지 않는다.
* [ ] Architecture의 루트 `main.py`, `app/core`와 `app/api` 책임을 따른다.
* [ ] `mcp_tutorial/`과 기존 대상 DB 실행 경계를 변경하지 않는다.
* [ ] Feature Spec과 구현의 차이 또는 차이 없음이 기록된다.
* [ ] 실행하지 못한 검증과 남은 위험이 기록된다.

## 미결정 사항

다음 항목은 구현 요청 전에 검토하여 해소하고 상태를 `Approved`로 변경한다.

* 루트 `pyproject.toml`의 Project Name과 초기 Version
* FastAPI, Uvicorn, Pydantic Settings, Pytest와 HTTP Client의 허용 Version 범위
* `AppSettings.app_name`과 `AppSettings.environment`의 기본값
* 환경변수 Prefix를 `APP_`로 통일할지 여부

## 검증 기록

현재 상태는 `Draft`이며 실제 구현 검증은 수행하지 않았다.

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 관련 테스트 | `uv run pytest` | 미실행 - 구현 전 |
| ASGI Import | `uv run python -c "from main import app"` | 미실행 - 구현 전 |
| 수동 Liveness | `uv run uvicorn main:app` 후 `GET /health` | 미실행 - 구현 전 |
| 문서 링크 | 저장소 내부 상대 링크 검사 | 미실행 |
| 기본 포맷 | `git diff --check` | 미실행 |

실행하지 못한 검증과 남은 위험:

* 의존성 Version과 설정 기본값이 확정되지 않아 구현을 시작할 수 없다.
* MCP, DB와 LLM 준비 상태는 후속 Readiness Feature에서 별도로 정의해야 한다.
