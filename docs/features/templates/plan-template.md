# Feature Plan 템플릿

> Plan은 Approved Spec을 기술적 구현 설계로 변환한다. Plan 작성·수정 단계에서는 실제 구현 코드와 Tasks를 만들지 않는다.

# `<Feature Name>` Plan

* Feature ID: `FEAT-NNNN`
* Status: `Draft`
* Development Track: `<Source Spec과 동일>`
* Source Spec: `<relative-link>` (`Approved`)

## Track별 작성 규칙

* `Lightweight`: 아래 절을 모두 길게 채우지 않는다. 구현 목표, 핵심 결정과 변경 파일, 실패·경계 처리, 검증, 미결정 사항과 검토 기록이 드러나는 최소 구조로 작성한다. 별도 공개 경계나 복잡한 흐름이 없으면 해당 절을 생략하거나 기술적 접근에 합치고, 자명한 대안과 Spec 설명을 반복하지 않는다. 요구사항 ID는 관련 결정과 검증에 연결한다.
* `Standard`: 적용 가능한 절을 모두 사용해 공개 경계, 정상·실패 흐름, 대안, 컴포넌트 책임과 요구사항 추적을 상세히 작성한다.

## 구현 목표

Spec의 어떤 결과를 이 Plan이 구현하는지 요약한다.

## 관련 기준과 준수 여부

* README 원칙: ...
* ADR: ...
* Architecture: ...
* Contract: ...

충돌하거나 변경이 필요한 기준 문서가 있다면 Plan을 진행하지 않고 기록한다.

Lightweight에서는 관련 기준과 충돌 여부만 간결하게 기록하고, 상위 문서 내용을 복사하지 않는다.

## 기술적 접근

* 기술 선택과 이유
* 고려한 대안과 기각 이유
* 불필요한 추상화와 범위 확장을 피하는 방법

Lightweight에서는 구현 결과를 바꾸는 결정과 자명하지 않은 선택 이유만 남긴다.

## 모듈과 파일 책임

| 파일 또는 모듈 | 책임 | 변경 유형 |
|---|---|---|
| `...` | ... | 추가/수정 |

## 공개 경계

외부에서 사용하는 Class, Protocol, Function, Method, Pydantic Model 또는 Tool Contract를 정의한다. Private Helper와 로컬 구현 상세는 고정하지 않는다.

```python
# 공개 경계 예시
```

공개 경계가 없는 Lightweight Feature에서는 이 절을 생략할 수 있다.

## 동작과 데이터 흐름

정상 흐름, Lifecycle과 상태 전이를 기술한다.

단순한 단일 흐름의 Lightweight Feature에서는 기술적 접근에 합칠 수 있다.

## 오류·보안·경계 처리

* 실패 동작과 예외 형식
* 권한과 Fail Closed
* Timeout, 연결 종료와 정리 책임

해당 Feature와 무관한 항목은 제거한다.

## 테스트 전략

* 단위 테스트
* 통합 테스트
* 수동 검증
* Spec Acceptance Criteria와의 연결

## 요구사항 추적

| Spec 요구사항 | Plan 설계 | 검증 전략 |
|---|---|---|
| `FR-001` | ... | ... |

Lightweight에서는 요구사항 Coverage가 핵심 결정과 검증에서 명확하면 표를 간결하게 작성하고 같은 설명을 반복하지 않는다.

## 미결정 사항

`Approved`로 변경하기 전에 Tasks와 구현에 영향을 주는 기술 질문을 해소한다.

* ...

## 검토 기록

Codex 검토는 필수다. 고위험 변경에서 추가 Reviewer를 사용하는 경우 행을 추가한다. 의견 원문 전체가 아니라 발견 사항과 최종 결정을 기록한다.

| Reviewer | 발견 사항 | 심각도 | 결정과 근거 | 상태 |
|---|---|---|---|---|
| Codex | ... | High/Medium/Low | ... | Open/Resolved/Rejected |

## Plan 승인 조건

* [ ] Source Spec에 Development Track이 있으면 해당 Track의 문서화 수준을 적용함
* [ ] Approved Spec의 모든 요구사항을 추적함
* [ ] ADR, Architecture와 Contract에 충돌하지 않음
* [ ] 공개 경계, 실패 동작과 테스트 전략이 명확함
* [ ] 기술 미결정 사항이 없음
* [ ] 필수 Codex 검토 의견이 해결되거나 기각 근거가 기록됨
