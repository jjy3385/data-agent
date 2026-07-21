# AI-Assisted Development Protocol

> 이 문서는 승인된 Feature Tasks를 실제 코드와 테스트로 구현할 때 사용하는 작업 단위, AI 요청 방식과 검토 절차를 정의한다. `Spec → Plan → Tasks` 전체 흐름은 [Feature 기반 개발 안내](features/README.md)를, 프로젝트 방향과 설계 경계는 README, ADR, Architecture와 Contract를 따른다.

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
7. Claude Code가 Approved Spec과 Plan으로 `tasks.md`를 생성한다. 이 단계에서는 코드를 만들지 않는다.
8. Spec, Plan과 Tasks의 Coverage, 충돌과 의존 순서를 검토한 뒤 사용자가 Tasks를 `Approved`로 변경한다.
9. Claude Code가 Task 하나씩 코드와 관련 테스트를 구현한다.
10. Codex가 구현을 검토하고 결과를 Tasks에 반영한다. 고위험 구현은 필요에 따라 추가 Reviewer의 독립 검토를 받는다.
11. 모든 Acceptance Criteria와 검증이 충족되면 Tasks를 `Verified`로 변경하고 Roadmap을 완료 처리한다.

상위 문서는 자동으로 하위 문서와 동기화되지 않는다. Approved Spec이 변경되면 Plan과 Tasks를, Approved Plan이 변경되면 Tasks를 재검토한다. 일관성이 다시 확인될 때까지 영향받는 구현을 중단한다.

```text
spec.md       무엇을 왜 만드는가
  ↓ Approved
plan.md       기술적으로 어떻게 구현하는가
  ↓ Approved
tasks.md      어떤 순서와 단위로 구현하는가
  ↓ Approved
코드와 테스트
```

각 구현 Task는 아래의 원자 단위 개발 프로토콜을 따른다.

### Development Track 적용

Lightweight와 Standard 모두 위 단계와 승인 Gate를 그대로 따른다. Track별 선택 기준과 문서 최소 정보는 [Feature 기반 개발 안내](features/README.md#development-track)를 기준으로 한다.

Lightweight Feature는 다음과 같이 간소화한다.

1. 사용자는 Spec의 범위, 실패 시나리오, Acceptance Criteria와 Track 선택 근거를 확인한다.
2. Plan은 핵심 기술 결정, 변경 파일, 실패 동작과 검증 방법 중심으로 작성하고 Codex는 이 결정과 범위 초과 여부를 검토한다.
3. Tasks는 요구사항 Coverage, 순서, 대상 파일, 구현과 검증만 남기며 같은 완료 조건을 Task마다 반복하지 않는다.
4. 구현 중에는 현재 Task만 읽고 코드와 관련 테스트를 함께 작성한 뒤 실행 명령과 결과를 기록한다.
5. Feature 완료 시 전체 검증, Plan 차이, 남은 위험과 Codex 구현 검토 결과를 확인한다.

Standard Feature는 공개 경계, 정상·실패 흐름, 대안, 컴포넌트 책임과 요구사항 추적을 상세히 기록하고 검토한다. Lightweight 구현이 Standard 조건으로 확대되면 즉시 구현을 중단하고 Spec, Plan과 Tasks를 순서대로 갱신·재승인한다.

## 3. 원자 작업 단위

AI에게 요청 가능한 단위:

- SQL 쿼리 하나
- 함수 하나
- Pydantic 모델 하나
- 테스트 케이스 하나
- 예외 처리 개선 하나

AI에게 요청하지 않는 단위:

- “Week 1 전체 구현”
- “schema_service.py 전부 만들어줘”
- “Slack 연동 다 해줘”
- “프로젝트 구조 알아서 짜줘”

## 4. 표준 작업 루프

1. 내가 먼저 목적을 쓴다.
2. 입력/출력 타입을 정의한다.
3. 실패 케이스를 적는다.
4. 구현할 동작과 해당 테스트를 AI에게 함께 요청한다.
5. 코드를 직접 읽는다.
6. 관련 테스트를 로컬에서 실행한다.
7. 정상·실패 동작과 Feature 완료 조건을 확인한다.
8. 이해한 내용을 짧게 기록한다.

## 5. AI 요청 템플릿

```text
다음 함수의 내부 구현만 작성해줘.

목표:
입력:
출력:
제약:
실패 케이스:
기존 코드:
관련 Feature 디렉터리:
현재 Task ID:
원하는 스타일:

주의:
- Approved Plan 또는 현재 Task에 명시되지 않은 새 파일을 만들지 마.
- 외부 라이브러리를 임의로 추가하지 마.
- 요청한 동작의 정상·실패 테스트를 함께 작성해.
- 50줄 이내로 작성해.
- 구현 후 왜 이렇게 작성했는지 설명해.

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
