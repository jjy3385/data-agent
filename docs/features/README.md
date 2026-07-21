# Feature 기반 개발 안내

> 이 디렉터리는 GitHub Spec Kit 도구를 설치하지 않고 `Spec → Plan → Tasks` 철학만 적용하기 위한 프로젝트 자체 작업 공간이다. 요구사항, 기술 계획과 실행 작업을 분리하여 Claude Code가 문서를 생성·수정하고, 사용자와 Codex가 단계별로 검토할 수 있게 한다. 추가 Reviewer의 독립 검토는 변경 위험에 따라 선택한다.

## 기본 원칙

```text
Spec 승인
  → Plan 생성·검토·승인
  → Tasks 생성·일관성 검토·승인
  → Task 단위 구현·테스트
  → 구현 검토
  → Verified
```

디렉터리와 템플릿 자체가 문서를 자동 생성하거나 동기화하지 않는다. 사용자가 Claude Code에 다음 단계의 문서 생성 또는 수정을 요청하면 Claude Code가 저장소 파일을 직접 변경한다.

## 디렉터리 구조

```text
docs/features/
├── README.md
├── templates/
│   ├── spec-template.md
│   ├── plan-template.md
│   └── tasks-template.md
└── NNNN-feature-name/
    ├── spec.md
    ├── plan.md
    └── tasks.md
```

세 문서는 한꺼번에 만들지 않는다.

1. Feature를 시작할 때 `spec.md`를 작성하고 Development Track을 선택한다.
2. `spec.md`가 `Approved`가 되면 Claude Code가 `plan.md`를 생성한다.
3. `plan.md`가 `Approved`가 되면 Claude Code가 `tasks.md`를 생성한다.
4. `tasks.md`가 `Approved`가 된 뒤에만 구현을 시작한다.

## 문서별 책임

| 문서 | 답하는 질문 | 포함하는 내용 | 포함하지 않는 내용 |
|---|---|---|---|
| `spec.md` | 무엇을 왜 만드는가? | 목적, 범위, 요구사항, 시나리오, Acceptance Criteria | 기술 스택, 함수명, 파일 경로, 구현 순서 |
| `plan.md` | 기술적으로 어떻게 구현하는가? | 기술 선택, 모듈 책임, 공개 경계, 오류·보안·테스트 전략 | 구현 체크리스트, 실제 코드 |
| `tasks.md` | 어떤 순서와 단위로 구현하는가? | 선행 관계, 대상 파일, 동작과 테스트, 완료·검증 기록 | 새로운 요구사항이나 승인되지 않은 설계 |

ADR은 선택 이유, Architecture는 시스템 연결과 책임, Contract는 정확한 컴포넌트 간 형식을 계속 담당한다. Feature 문서는 관련 기준 문서를 링크하고 내용을 복사하지 않는다.

## Development Track

모든 Feature는 `Spec → Plan → Tasks → 구현` 순서와 기존 승인 Gate를 동일하게 적용한다. Development Track은 단계를 생략하는 규칙이 아니라 문서의 상세도와 반복 수준을 조절하는 규칙이다. 이 정책 도입 이후 시작하는 Feature는 선택한 Track과 근거를 `spec.md` 상단에 기록하고 사용자가 Spec과 함께 승인한다.

### Lightweight

다음 조건을 모두 만족하는 단일 컴포넌트의 저위험 Feature에 적용한다.

* 보안 경계, 권한, 대상 DB 접근이나 SQL 실행 경계를 변경하지 않는다.
* 공개 Contract나 ADR을 추가하거나 변경하지 않는다.
* DB Migration 또는 외부 시스템 연결·자원 Lifecycle을 포함하지 않는다.
* 변경이 작고 되돌리기 쉬우며 로컬 자동 테스트 또는 간단한 수동 검증으로 확인할 수 있다.

Lightweight 문서도 요구사항, 핵심 기술 결정, 실패 동작, 변경 파일, 검증과 Reviewer 결정을 추적해야 한다. 다만 상위 문서의 설명을 반복하지 않고 다음 최소 정보만 남긴다.

| 문서 | 최소 정보 |
|---|---|
| `spec.md` | 목적, 포함·제외 범위, 관찰 가능한 요구사항·Acceptance Criteria, 실패 시나리오, Track 선택 근거 |
| `plan.md` | 구현 결과를 바꾸는 핵심 결정, 변경 파일, 실패·경계 처리, 검증 방법, 미결정 사항, Codex 검토 결과 |
| `tasks.md` | 요구사항 Coverage, Task 순서, Task별 대상 파일·구현·검증·상태, Feature 전체 검증 결과 |

별도 공개 경계가 없으면 Plan의 공개 경계 절을, 복잡한 흐름이 없으면 상세 상태 전이를, 자명한 선택이면 긴 대안 비교를 생략하거나 관련 절에 합칠 수 있다. 같은 요구사항과 완료 조건을 여러 절이나 Task에 반복하지 않는다.

### Standard

Lightweight 조건을 하나라도 만족하지 않거나 다음 중 하나에 해당하면 Standard를 적용한다.

* ACL, Metadata 격리, SQL Guardrail 또는 Fail Closed 경계를 변경한다.
* Contract나 ADR을 추가하거나 변경한다.
* DB, MCP, LLM 또는 외부 시스템 연결·자원 Lifecycle에 영향을 준다.
* 여러 컴포넌트의 책임이나 호출 흐름을 변경한다.
* 실패 시 보안, 데이터 또는 운영 영향이 크다.

Standard는 관련 템플릿의 적용 가능한 절을 모두 사용하고 정상·실패 흐름, 공개 경계, 대안, 요구사항 추적과 검증 책임을 상세히 기록한다.

구현 범위가 바뀌어 Lightweight 조건을 벗어나면 구현을 중단하고 Spec의 Track을 Standard로 변경한다. 이어서 Plan과 Tasks를 보완·재검토하고 다시 승인한 뒤 구현을 재개한다.

이 정책을 도입하기 전에 이미 Spec, Plan과 Tasks 작성이 진행된 Feature는 Track을 소급 기록하거나 문서 길이를 줄이기 위한 목적으로만 다시 작성하지 않는다. 기존 승인 문서의 필수 정보와 추적성이 충족되면 해당 문서를 그대로 따르고, 이후 새로 시작하는 Feature부터 Development Track을 적용한다.

## 상태와 Quality Gate

### Spec

```text
Draft → Approved
```

`Approved` 조건:

* 정책 도입 이후 시작한 Feature는 Development Track과 선택 근거가 기록됐다.
* 포함·제외 범위가 명확하다.
* 요구사항과 Acceptance Criteria가 관찰·검증 가능하다.
* 정상·실패 시나리오가 있다.
* Plan에 영향을 주는 요구사항 미결정 사항이 없다.

### Plan

```text
Draft → Approved
```

`Approved` 조건:

* Source Spec에 Development Track이 있으면 해당 Track의 문서화 수준을 적용했다.
* 승인된 Spec의 모든 요구사항을 추적한다.
* README, ADR, Architecture와 Contract에 어긋나지 않는다.
* 공개 경계, 오류 처리, 보안과 테스트 전략이 명확하다.
* Codex 검토 결과가 반영 또는 기각 사유와 함께 기록됐다.
* Tasks에 영향을 주는 기술 미결정 사항이 없다.

### Tasks

```text
Draft → Approved → In Progress → Verified
```

`Approved` 조건:

* Source Spec에 Development Track이 있으면 해당 Track의 Task 상세도를 적용했다.
* 승인된 Spec 요구사항과 Plan 설계를 빠짐없이 추적한다.
* 의존 순서와 변경 대상 파일이 명확하다.
* 코드 동작과 해당 테스트 또는 재현 가능한 검증이 같은 Task에 포함된다.

`Verified` 조건:

* 모든 Task가 완료됐다.
* 관련 자동 테스트와 수동 검증 결과가 기록됐다.
* Codex 구현 검토 결과가 해결 또는 명시적으로 기각됐다.
* Spec Acceptance Criteria와 Plan 준수 여부가 확인됐다.

## AI와 사용자의 역할

| 참여자 | 기본 역할 |
|---|---|
| 사용자 | 범위와 최종 결정 승인, 상충하는 리뷰 판단 |
| Claude Code | 승인된 상위 문서를 기준으로 Plan·Tasks 생성 및 Task 단위 구현 |
| Codex | Architecture, Contract, 보안 경계, 코드와 테스트 중심 검토 |
| 추가 Reviewer | 누락, 과도한 설계, 대안과 전체 기능 관점의 선택적 독립 검토 |

AI의 의견은 자동 승인되지 않는다. 어떤 의견을 반영할지는 사용자가 판단하며, 승인된 결과만 기준 문서에 남긴다.

## 검토 정책과 기록

별도 Review 문서를 만들지 않는다.

* Plan과 구현의 Codex 검토는 필수다.
* 보안 경계, Contract, ADR 또는 여러 컴포넌트에 영향을 주는 고위험 변경은 추가 Reviewer의 독립 검토를 권장한다.
* 추가 Reviewer 검토는 선택 사항이며, 검토가 없다는 이유만으로 Plan 승인이나 Tasks의 `Verified` 전환을 막지 않는다.
* Plan에 대한 의견과 결정은 `plan.md`의 `검토 기록` 절에 기록한다.
* 구현에 대한 의견과 처리 결과는 `tasks.md`의 해당 Task 또는 `최종 구현 검토` 절에 기록한다.
* 긴 대화 원문을 복사하지 않고 발견 사항, 심각도, 결정과 처리 상태만 남긴다.

추가 Reviewer를 사용하는 경우 가능한 한 Codex의 결론을 보기 전에 독립적으로 검토한다. 의견이 충돌하면 사용자가 Spec, 프로젝트 원칙과 검증 근거를 기준으로 결정한다.

## 변경 전파 규칙

문서는 자동으로 동기화되지 않는다. 상위 문서가 바뀌면 사용자가 Claude Code에 하위 문서 재검토를 요청한다.

| 변경 | 필요한 조치 |
|---|---|
| Approved `spec.md` 변경 | `plan.md`와 `tasks.md`를 재검토하고 구현을 일시 중단 |
| Approved `plan.md` 변경 | `tasks.md`를 재검토하고 영향받는 구현을 일시 중단 |
| `tasks.md` 변경 | 완료 상태, 테스트와 구현 범위를 재확인 |
| Development Track 변경 | Spec의 Track과 근거를 변경하고 Plan·Tasks를 재검토·재승인한 뒤 구현 재개 |
| 프로젝트 전체 설계 변경 | ADR·Architecture·Contract를 먼저 승인한 뒤 Feature 문서 갱신 |

요구사항 문제는 `spec.md`, 기술 설계 문제는 `plan.md`, 작업 누락·순서·검증 문제는 `tasks.md`에서 수정한다. 코드만 먼저 고쳐서 문서와 불일치하게 만들지 않는다.

## Claude Code 요청 예시

Spec이 승인된 뒤:

```text
FEAT-NNNN의 Approved spec.md와 plan-template.md, 관련 기준 문서를 읽고
Spec에 기록된 Development Track의 문서화 수준에 맞춰 plan.md를 작성해줘.
구현 코드와 tasks.md는 만들지 마.
```

Plan 검토 의견을 반영할 때:

```text
Codex와 선택적으로 받은 추가 Reviewer의 검토 결과를 판단하여 plan.md를 수정해줘.
반영 여부와 이유를 검토 기록 절에 기록하고 구현은 시작하지 마.
Spec 변경이 필요한 의견은 임의로 반영하지 말고 보고해줘.
```

Plan이 승인된 뒤:

```text
Approved spec.md와 plan.md, tasks-template.md를 읽고 tasks.md를 작성해줘.
Spec에 기록된 Development Track의 문서화 수준을 적용하고 구현 코드는 아직 수정하지 마.
```

## Feature 목록

현재 단계와 상태는 각 Feature 디렉터리에서 가장 최근에 생성된 문서 상단을 기준으로 확인한다.

| Feature | Roadmap 책임 |
|---|---|
| [FEAT-0001 FastAPI Bootstrap](0001-fastapi-bootstrap/spec.md) | Week 1 FastAPI 프로젝트 기본 구조 |

## 관련 문서

* [프로젝트 문서 안내](../README.md)
* [AI-Assisted Development Protocol](../development-protocol.md)
* [MVP Roadmap](../mvp/roadmap.md)
