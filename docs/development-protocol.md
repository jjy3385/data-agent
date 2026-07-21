# AI-Assisted Development Protocol

> 이 문서는 Feature Specification을 실제 코드와 테스트로 구현할 때 사용하는 작업 단위, AI 요청 방식과 검토 절차를 정의한다. 큰 기능의 범위와 완료 조건은 `docs/features/`, 프로젝트 방향과 설계 경계는 README, ADR, Architecture와 Contract를 따른다.

## 1. 역할 분리

- Developer: 요구사항 정의, 인터페이스 설계, 타입 정의, 코드 리뷰, 최종 승인
- AI Agent: 구현 초안, 테스트 코드, 대안 제시, 리팩터링 제안, 문서화 보조

## 2. Feature 기반 작업

여러 파일, 공개 Interface, Lifecycle, 보안 경계 또는 여러 테스트가 필요한 기능은 구현 전에 [`docs/features/`](features/README.md)에 Feature Specification을 작성한다.

작업 순서:

1. Roadmap에서 다음 책임 단위를 선택한다.
2. 관련 ADR, Architecture와 Contract를 확인한다.
3. Feature Specification을 `Draft`로 작성한다.
4. 범위, 공개 경계, 실패 동작, 미결정 사항과 완료 조건을 검토하고 `Approved`로 변경한다.
5. 첫 Task를 시작할 때 `In Progress`로 변경한다.
6. Feature를 작고 검토 가능한 구현 Task로 나눈다.
7. AI Agent에는 Task 하나씩 요청한다.
8. 각 코드 동작과 관련 테스트를 같은 Task에서 구현하고 직접 검토한다.
9. Feature 전체 검증과 검증 기록을 완료한 후 `Verified`로 변경한다.
10. Roadmap 항목을 완료 처리한다.

Feature Specification이 있더라도 AI Agent에게 Feature 전체를 한 번에 구현하도록 요청하지 않는다. 각 Task는 아래의 원자 단위 개발 프로토콜을 따른다.

```text
Feature Specification
  → 작은 구현 Task
  → 함수·모델·쿼리와 해당 테스트
  → Feature 전체 검증
```

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
관련 Feature Specification:
원하는 스타일:

주의:
- Feature Specification 또는 현재 Task에 명시되지 않은 새 파일을 만들지 마.
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
