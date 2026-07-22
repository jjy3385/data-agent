# AI-Assisted Development Protocol

> 이 문서는 Approved Plan을 실제 코드와 테스트로 구현하고 그 결과를 Tasks에 기록할 때 사용하는 작업 단위, AI 요청 방식과 검토 절차를 정의한다. `Spec → Plan → 구현·테스트 → Tasks 기록 → 구현 검토` 전체 흐름은 [Feature 기반 개발 안내](features/README.md)를, 프로젝트 방향과 설계 경계는 README, ADR, Architecture와 Contract를 따른다.

## 1. 역할 분리

- Developer: 요구사항 정의, 인터페이스 설계, 타입 정의, 코드 리뷰, 최종 승인
- AI Agent: 구현 초안, 테스트 코드, 대안 제시, 리팩터링 제안, 문서화 보조

## 2. Feature 기반 작업

여러 파일, 공개 Interface, Lifecycle, 보안 경계 또는 여러 테스트가 필요한 기능은 [`docs/features/`](features/README.md) 아래에서 다음 순서로 진행한다.

1. 사용자와 AI가 `spec.md`에 무엇을 왜 만드는지 정의하고 Development Track을 선택한다.
2. 사용자가 Spec을 검토하고 `Approved`로 변경한다.
3. Claude Code가 Approved Spec과 관련 기준 문서를 읽고 `plan.md`를 생성한다. 이 단계에서는 코드와 Tasks를 만들지 않는다.
4. Codex가 Plan을 검토하고 사용자가 반영 여부를 결정한다. 보안 경계, Contract, ADR 또는 여러 컴포넌트에 영향을 주는 고위험 Plan은 필요에 따라 추가 Reviewer의 독립 검토를 받는다.
5. Claude Code가 결정된 의견을 Plan의 `검토 기록` 절과 설계에 반영한다.
6. 사용자가 Plan을 검토하고 `Approved`로 변경한다.
7. Claude Code가 Approved Plan 범위의 Feature 전체 코드와 관련 정상·실패 테스트를 구현하고 검증한다.
8. Plan과 다른 중요한 설계, 공개 경계, 의존성 또는 파일 책임이 필요하면 구현을 중단하고 Plan을 수정·재검토한다.
9. 구현과 검증이 끝나면 Claude Code가 실제 변경, 테스트 결과, Plan과의 차이와 남은 위험을 기준으로 `tasks.md`를 `Review` 상태로 작성한다.
10. Codex가 실제 코드, 테스트와 Tasks 기록을 함께 검토한다. 고위험 구현은 필요에 따라 추가 Reviewer의 독립 검토를 받는다.
11. Claude Code가 발견 사항을 수정하고 관련 검증과 Tasks 기록을 갱신한다.
12. 모든 Acceptance Criteria와 검증이 충족되면 Tasks를 `Verified`로 변경하고 Roadmap을 완료 처리한다.

상위 문서는 자동으로 구현이나 Tasks 기록과 동기화되지 않는다. Approved Spec이 변경되면 Plan을, Approved Plan이 변경되면 영향받는 구현을 재검토한다. 일관성이 다시 확인될 때까지 구현을 중단하고 재구현·재검증 후 Tasks를 실제 결과로 갱신한다.

```text
spec.md       무엇을 왜 만드는가
  ↓ Approved
plan.md       기술적으로 어떻게 구현하는가
  ↓ Approved
코드와 테스트
  ↓ 구현·검증 완료
tasks.md      실제로 무엇을 구현하고 어떻게 검증했는가
  ↓ Codex Review
Verified
```

Approved Plan이 구현 승인 기준이며 Tasks는 사전 승인 문서가 아니다.

### Development Track 적용

Lightweight와 Standard 모두 Spec과 Plan 승인 Gate를 동일하게 적용한다. Track별 선택 기준과 Plan·구현 검증·사후 Tasks 기록의 상세도는 [Feature 기반 개발 안내](features/README.md#development-track)를 기준으로 한다.

Lightweight Feature는 다음과 같이 간소화한다.

1. 사용자는 Spec의 범위, 실패 시나리오, Acceptance Criteria와 Track 선택 근거를 확인한다.
2. Plan은 핵심 기술 결정, 변경 파일, 실패 동작과 검증 방법 중심으로 작성하고 Codex는 이 결정과 범위 초과 여부를 검토한다.
3. Claude Code는 Approved Plan 범위의 코드와 관련 테스트를 함께 구현하고 검증한다.
4. Tasks는 실제 요구사항 Coverage, 변경 파일, 구현 결과와 검증만 남기며 같은 완료 조건을 반복하지 않는다.
5. Feature 완료 시 전체 검증, Plan 차이, 남은 위험과 Codex 구현 검토 결과를 확인한다.

Standard Feature는 공개 경계, 정상·실패 흐름, 대안, 컴포넌트 책임과 요구사항 추적을 상세히 기록하고 검토한다. Lightweight 구현이 Standard 조건으로 확대되면 즉시 구현을 중단하고 Spec과 Plan을 순서대로 갱신·재승인한 뒤 구현을 재개하며, Tasks는 최종 실제 결과를 기록한다.

## 3. 구현 작업 단위

AI에게 요청 가능한 기본 단위:

- 하나의 Approved Feature Plan 전체
- 하나의 Contract, 함수, 쿼리 또는 테스트처럼 명확한 책임 단위
- Codex 검토에서 발견된 하나의 수정 묶음과 관련 회귀 테스트

AI에게 요청하지 않는 단위:

- “Week 1 전체 구현”
- 여러 Roadmap Feature를 한 번에 구현
- “프로젝트 구조 알아서 짜줘”

Claude Code는 Feature 내부 구현 순서를 스스로 나눌 수 있지만 Approved Plan 밖의 리팩터링, 파일 이동, 공개 경계 변경이나 의존성 추가를 임의로 포함하지 않는다.

## 4. 표준 작업 루프

1. Approved Spec과 Plan, 관련 기준 문서를 확인한다.
2. Plan 범위의 코드와 정상·실패 테스트를 함께 구현한다.
3. Plan 이탈이 필요하면 구현을 중단하고 이유와 영향을 보고한다.
4. 관련 자동 테스트와 필요한 수동 검증을 실행한다.
5. 실제 구현·검증 결과로 `tasks.md`를 `Review` 상태로 작성한다.
6. Codex가 코드, 테스트와 Tasks 기록을 검토한다.
7. 발견 사항을 수정하고 회귀 테스트와 Tasks 기록을 갱신한다.
8. 정상·실패 동작, Spec Acceptance Criteria와 Plan 준수를 확인한 뒤 `Verified`로 변경한다.

## 5. AI 요청 템플릿

```text
관련 Feature: FEAT-NNNN
Source Spec: <Approved spec.md>
Source Plan: <Approved plan.md>

주의:
- Approved Plan 범위의 Feature 전체 코드와 관련 정상·실패 테스트를 구현해.
- Plan과 다른 중요한 설계, 공개 경계, 의존성 또는 파일 책임이 필요하면 구현을 중단하고 먼저 보고해.
- 외부 라이브러리를 임의로 추가하지 마.
- 현재 Feature와 관련 없는 리팩터링이나 파일 이동을 하지 마.
- 구현과 검증이 끝나면 실제 결과를 기반으로 tasks.md를 Review 상태로 작성해.
- 변경 파일, 실행한 테스트와 결과, Plan 차이, 미검증 항목과 남은 위험을 기록해.

```

## 6. 병합 기준

AI 생성 코드는 다음 조건을 만족해야 병합한다.

내가 코드 흐름을 설명할 수 있다.
실패 케이스가 처리되어 있다.
테스트 또는 수동 검증 로그가 있다.
README의 Design Principles를 위반하지 않는다.
보안 관련 로직은 낙관적으로 통과시키지 않는다.

## 7. 학습 노트

각 기능 완료 후 docs/learning/weekXX.md에 기록한다.

오늘 구현한 것
새로 이해한 개념
헷갈린 부분
AI가 제안했지만 채택하지 않은 것
다음 리팩터링 후보
