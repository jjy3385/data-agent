# FastAPI 실행 기반 Spec

> 이 문서는 후속 Backend Feature를 구현하기 전에 필요한 최소 애플리케이션 실행 기반의 요구사항과 범위를 정의한다. 기술 의존성, 함수명, 파일 배치와 구현 순서는 Spec 승인 후 작성할 `plan.md`에서 결정한다.

* Feature ID: `FEAT-0001`
* Status: `Draft`
* Roadmap: [Week 1 - FastAPI 프로젝트 기본 구조](../../mvp/roadmap.md#week-1-business-metadata--security-foundation)

## 목적

후속 MCP, DB, LLM과 Workflow Feature가 공통으로 사용할 실행·설정·테스트 기반을 제공한다. 개발자는 Backend 애플리케이션을 시작하고, 프로세스가 살아 있는지 확인하고, 기본 테스트를 반복 실행할 수 있어야 한다.

## 범위

포함:

* 독립적으로 실행 가능한 최소 Backend 애플리케이션 기반
* 시작 전에 검증되는 최소 애플리케이션 설정
* 후속 자원 초기화와 정리를 연결할 수 있는 Application Lifecycle 기반
* 외부 의존성과 무관한 Liveness 확인
* 설정, 시작·종료와 Liveness 동작의 자동 검증 기반

제외:

* MCP Server와 MCP Client Manager의 시작·종료
* Admin DB와 대상 DB 연결
* LLM Provider
* RuntimeIntent, QueryPlan과 SQL Guardrail
* 외부 의존성 준비 여부를 나타내는 Readiness
* Slack 연동, 인증, 권한과 업무 API
* 전체 Docker Compose 애플리케이션 구성

## 사용자 또는 시스템 시나리오

### 시나리오 1: 개발자가 Backend 실행 상태를 확인한다

* Given: 지원되는 최소 설정이 준비되어 있다.
* When: 개발자가 Backend 애플리케이션을 시작하고 Liveness Endpoint를 호출한다.
* Then: 애플리케이션이 정상 시작되고 HTTP 200과 `{ "status": "ok" }`를 반환한다.

### 시나리오 2: 애플리케이션이 정상 종료된다

* Given: Backend 애플리케이션이 실행 중이다.
* When: 정상 종료가 요청된다.
* Then: Application Lifecycle이 오류 없이 종료된다.

### 실패 시나리오: 유효하지 않은 설정

* Given: 지원하지 않는 애플리케이션 설정값이 입력되어 있다.
* When: Backend 애플리케이션 시작을 시도한다.
* Then: 설정 오류를 명확히 표시하고 정상 상태인 것처럼 시작하지 않는다.

## 기능 요구사항

* `FR-001`: 개발자는 저장소 루트에서 Backend 애플리케이션을 일관된 명령으로 시작할 수 있어야 한다.
* `FR-002`: 시스템은 애플리케이션 설정을 시작 전에 검증하고 유효하지 않은 값을 거부해야 한다.
* `FR-003`: 시스템은 후속 Feature가 자원 초기화와 정리를 연결할 수 있는 시작·종료 Lifecycle을 제공해야 한다.
* `FR-004`: 시스템은 외부 의존성을 확인하지 않는 `GET /health` Liveness Endpoint를 제공해야 한다.
* `FR-005`: `GET /health`는 HTTP 200과 정확히 `{ "status": "ok" }`를 반환해야 한다.
* `FR-006`: 개발자는 설정, 시작·종료와 Liveness 동작을 자동 테스트로 검증할 수 있어야 한다.

## 비기능 요구사항

* `NFR-001`: `/health`는 MCP, DB와 LLM의 준비 상태를 성공으로 표현해서는 안 된다.
* `NFR-002`: 이 Feature는 `mcp_tutorial/`의 실행환경과 코드를 변경하거나 재사용하지 않아야 한다.
* `NFR-003`: 후속 Feature와 무관한 인증, DB, MCP, LLM 의존성을 포함하지 않아야 한다.

## Acceptance Criteria

* [ ] 저장소 루트에서 Backend 애플리케이션을 시작할 수 있다.
* [ ] 지원되는 설정으로 애플리케이션이 정상 시작하고 종료된다.
* [ ] 지원하지 않는 설정은 시작 전에 거부된다.
* [ ] `GET /health`가 HTTP 200과 정확히 `{ "status": "ok" }`를 반환한다.
* [ ] `/health`가 MCP, DB 또는 LLM 준비 상태를 검사하지 않는다.
* [ ] Readiness Endpoint는 이 Feature에 포함되지 않는다.
* [ ] 설정, 시작·종료와 Liveness의 자동 테스트가 존재한다.
* [ ] `mcp_tutorial/` 파일이 변경되지 않는다.

## 가정과 제약

* Backend Framework와 루트 진입점의 상위 Architecture 기준은 [프로젝트 모듈 구조](../../architecture/project-structure.md)를 따른다.
* 현재 Feature는 대상 DB 실행 경계를 구현하지 않으므로 새로운 ADR이나 MCP Tool Contract를 만들지 않는다.
* 상세 기술 선택과 공개 Interface는 이 Spec을 변경하지 않고 Plan에서 결정할 수 있어야 한다.

## 미결정 사항

현재 요구사항과 범위에 영향을 주는 미결정 사항은 없다. 기술 의존성 Version, 설정 필드와 기본값, 환경변수 규칙, 함수명과 파일 배치는 Plan에서 결정한다.

## 관련 기준 문서

* [프로젝트 README](../../../README.md)
* [MVP 범위와 대표 시나리오](../../mvp/scope.md)
* [MVP 완료 기준](../../mvp/acceptance-criteria.md)
* [프로젝트 모듈 구조](../../architecture/project-structure.md)
* [컴포넌트 책임과 경계](../../architecture/component-boundaries.md)
