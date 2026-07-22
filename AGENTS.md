# AI 에이전트 작업 지침 (AGENTS.md)

## 이 파일의 목적

이 파일은 AI 코딩 에이전트가 프로젝트의 설계 방향과 MVP 범위를 유지하면서 안전하게 작업하기 위한 저장소 공통 지침이다.

프로젝트 철학과 전체 구조의 기준 문서는 `README.md`다. 상세 설계를 이 파일에 반복해서 복사하지 않고 아래 문서 지도를 따라 필요한 기준 문서를 직접 확인한다.

## 작업 전 확인

1. 작업을 시작하기 전에 `README.md`의 절대 설계 원칙과 전체 아키텍처를 확인한다.
2. 기능 범위가 불명확하면 `docs/mvp/scope.md`를 확인한다.
3. 구현 순서나 현재 우선순위를 판단할 때는 `docs/mvp/roadmap.md`를 확인한다.
4. 변경 대상과 관련된 Architecture, Contract와 ADR을 코드보다 먼저 읽는다.
5. Feature 작업이면 `docs/features/README.md`와 해당 디렉터리의 `spec.md`, `plan.md`, `tasks.md` 중 현재 단계에 존재하는 문서를 확인한다.
6. 기존 사용자 변경사항을 보존하고 현재 작업과 관련 없는 파일을 수정하지 않는다.

## 문서 선택 기준

| 작업 또는 질문 | 기준 문서 |
|---|---|
| 프로젝트 철학과 전체 방향 | `README.md` |
| 구성요소 책임과 요청 흐름 | `docs/architecture/` |
| 정확한 입출력, 타입과 불변조건 | `docs/contracts/` |
| 설계 결정, 대안과 선택 이유 | `docs/adr/` |
| MVP 범위, 로드맵과 완료 기준 | `docs/mvp/` |
| 현재 기능의 요구사항, 구현 계획과 실제 구현·검증 기록 | `docs/features/` |
| 개발 작업 단위와 검토 절차 | `docs/development-protocol.md` |

세부 문서를 찾기 어렵다면 `docs/README.md`에서 시작한다.

## 변경할 수 없는 핵심 경계

다음 규칙은 사용자가 명시적으로 설계 변경을 결정하고 관련 문서와 ADR을 함께 수정하지 않는 한 유지한다.

1. LLM은 대상 DB에 직접 연결하거나 SQL을 직접 실행하지 않는다.
2. 대상 DB 접근은 승인된 MCP Tool을 통해서만 수행한다.
3. FastAPI에는 MCP 장애 시 대상 DB로 직접 우회하는 Fallback을 만들지 않는다.
4. SQL은 실행 전에 ACL, QueryPlan Validation, SQL Guardrail과 구조적 Plan-SQL Match를 통과해야 한다.
5. 대상 DB 계정은 Read-Only이며 쓰기 권한을 부여하지 않는다.
6. 권한, Metadata, Contract 또는 실행 안전성이 불확실하면 Fail Closed한다.
7. MVP Workflow는 최대 Depth 2로 제한한다. SQL Self-Healing은 Post-MVP이며, 구현하는 경우 실행당 최대 1회로 제한한다.
8. 실제 Depth 2 대상과 PK는 Backend가 Depth 1 결과 범위 안에서 선택한다.
9. MVP는 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 Bounded Result를 Result Handle 없이 LLM에 직접 전달한다.
10. Result Store와 Result Handle은 Post-MVP 범위다. Post-MVP 전달 전략은 `docs/adr/0006-result-handle.md`를 따른다.
11. MVP는 FastAPI 워커 하나와 FastAPI가 관리하는 로컬 `stdio` MCP Server 하나를 전제로 한다.
12. MCP Server의 `stdout`은 MCP Protocol 전용이며 일반 로그는 `stderr` 또는 별도 Log Sink로 보낸다.

## 컴포넌트 책임

* Workflow Orchestrator: ACL, RuntimeIntent, Metadata Retrieval, QueryPlan, SQL Guardrail, Workflow Depth, XAI와 Audit을 통제한다.
* MCP Client Manager: 공식 MCP SDK Client, 장기 유지 Session, 요청 직렬화, MCP Call Timeout과 오류 변환을 담당한다.
* MCP Server: 대상 DB 연결, Read-Only Query Executor, DB Query Timeout, Maximum Returned Rows와 최소 실행 안전성을 담당한다.
* LLM Provider: 구조화된 제안을 생성하지만 SQL 실행 권한과 대상 선택 최종 권한을 갖지 않는다.

상세 경계는 `docs/architecture/component-boundaries.md`를 기준으로 한다.

## 구현 규칙

1. 작업 범위를 임의로 Post-MVP까지 확장하지 않는다.
2. Contract가 바뀌는 기능은 관련 `docs/contracts/` 문서를 코드보다 먼저 수정하거나 같은 변경 안에서 함께 수정한다.
3. 중요한 Architecture 결정이 바뀌면 기존 ADR의 상태를 확인한 뒤 관련 ADR을 수정하거나 새 ADR을 작성한다.
4. ADR에는 선택 이유와 대안을, Contract에는 현재 입출력 형식을 기록한다. 같은 상세 규칙을 여러 문서에 복제하지 않는다.
5. FastAPI 서비스 코드에서 대상 DB Driver나 직접 연결을 추가하지 않는다.
6. MCP Wire Protocol을 직접 구현하지 않고 공식 MCP SDK Client를 사용한다.
7. LLM이 반환한 Tool Call, QueryPlan, SQL 또는 Next Action을 신뢰하지 않고 Backend에서 검증한다.
8. Timeout은 계층별로 구분한다. MCP Client Manager는 MCP Call Timeout, MCP Server는 DB Query Timeout을 담당한다.
9. 새 기능에는 정상 경로뿐 아니라 권한 거부, Contract 오류, Timeout, 연결 종료와 Fail Closed 경로를 고려한다.
10. 문서 상단에는 한글로 목적, 범위와 관련 문서를 설명하고 영어 기술 용어는 필요한 경우 병기한다.
11. Feature 작업은 `Spec → Plan → 구현·테스트 → Tasks 기록 → 구현 검토` 순서를 따른다.
12. `spec.md`가 `Approved`가 아니면 `plan.md`를 생성하지 않는다. Plan 작성·수정 단계에서는 구현 코드와 `tasks.md`를 만들지 않는다.
13. `plan.md`가 `Approved`가 아니면 구현을 시작하지 않는다. Approved Plan은 해당 Feature 전체의 구현과 관련 테스트를 수행할 수 있는 승인 기준이다.
14. 구현과 검증이 끝나면 실제 변경, 테스트 결과, Plan과의 차이와 남은 위험을 기준으로 `tasks.md`를 `Review` 상태로 생성하거나 갱신한다. `tasks.md`는 구현 전 승인 문서가 아니다.
15. 구현 중 Approved Plan과 다른 중요한 설계, 공개 경계, 의존성 또는 파일 책임이 필요하면 작업을 중단하고 Plan을 수정·재검토한다. Approved Spec이 변경되면 Plan을 재검토하고 일관성 확인 전까지 영향받는 구현을 중단한다.
16. Spec, Plan, 구현 또는 Tasks 기록이 README, ADR, Architecture나 Contract와 충돌하면 임의로 해석하지 않고 충돌 위치와 영향을 먼저 보고한다.
17. Codex 구현 검토의 발견 사항과 처리 결과를 `tasks.md`에 기록하고 모든 완료 조건을 충족한 뒤에만 `Verified`로 변경한다.

## 작업 단위와 사용자 협업

* 하나의 요청은 하나의 Approved Feature Plan 또는 명확한 책임 단위로 제한한다. 여러 Roadmap Feature를 한 번에 구현하지 않는다.
* Approved Plan 범위에서는 Feature 전체 구현과 관련 테스트를 함께 수행할 수 있으며, AI Agent는 내부 구현 순서를 검토 가능한 단위로 나눈다.
* 요구사항이 기존 Architecture나 ADR과 충돌하면 구현 전에 충돌 위치와 영향을 사용자에게 설명한다.
* 의미 있는 설계 변경은 사용자의 결정 없이 임의로 확정하지 않는다.
* 기존 코드와 문서에서 확인할 수 있는 내용은 사용자에게 다시 묻기 전에 먼저 조사한다.
* 현재 작업과 무관한 리팩터링, 파일 이동이나 의존성 추가를 함께 수행하지 않는다.

상세 작업 방식은 `docs/development-protocol.md`를 따른다.

## 검증과 완료 조건

작업을 완료하기 전에 변경 위험에 비례해 다음을 확인한다.

1. 관련 테스트 또는 재현 가능한 수동 검증을 수행한다.
2. 권한 거부와 Fail Closed 경로가 유지되는지 확인한다.
3. Contract, Architecture, ADR과 구현이 서로 모순되지 않는지 확인한다.
4. Markdown 문서를 변경했다면 상대 링크와 후행 공백을 검사한다.
5. `git diff --check`로 기본 포맷 오류를 확인한다.
6. 변경한 파일, 검증 결과와 남은 위험을 사용자에게 보고한다.
7. 테스트하지 않은 내용을 검증했다고 표현하거나 미완료 작업을 완료로 표시하지 않는다.
