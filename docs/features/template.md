# 기능 명세 템플릿 (Feature Specification Template)

> 이 템플릿은 하나의 Feature를 구현·검증 가능한 Task로 나누기 위한 기본 구조다. 해당 기능과 무관한 예시 항목은 제거하되 범위, 공개 경계, 실패 동작과 완료 조건은 생략하지 않는다.

# `<Feature Name>`

* Feature ID: `FEAT-NNNN`
* 상태: `Draft`
* 관련 Roadmap 항목: `<link>`

## 목적

이 기능이 해결하는 문제와 구현 후 관찰할 수 있는 결과를 작성한다.

## 선행 조건과 의존성

* 먼저 완료되어야 하는 Feature, 환경 또는 승인된 결정
* 필요한 내부·외부 의존성

## 범위

포함:

* ...

제외:

* ...

## 관련 기준 문서

* ADR: ...
* Architecture: ...
* Contract: ...
* MVP Scope: ...
* Acceptance Criteria: ...

## 관찰 가능한 동작

### 정상 동작

1. ...
2. ...

### 실패 동작

* ...
* ...

## 공개 경계

외부에서 사용하는 Class, Protocol, Function, Method, Pydantic Model 또는 Tool Contract만 작성한다. 모든 Private Helper와 구현 상세를 미리 고정하지 않는다.

```python
# 공개 경계 예시
```

## 구현 대상

예상 수정·추가 파일:

* `...`

새 파일이나 외부 의존성을 추가해야 한다면 그 이유를 작성한다.

## 구현 Task

각 코드 Task에는 해당 동작의 테스트를 함께 포함한다. 테스트가 적합하지 않은 설정 Task에는 재현 가능한 검증 명령을 포함한다.

* [ ] Task 1: 동작과 해당 테스트 또는 검증
* [ ] Task 2: 동작과 해당 테스트 또는 검증
* [ ] Task 3: Feature 전체 회귀 검증

## 테스트와 완료 조건

Feature와 관련 있는 항목만 유지한다.

* [ ] 정상 경로가 검증됨
* [ ] 권한 거부가 검증됨
* [ ] Contract 오류가 검증됨
* [ ] Timeout 또는 연결 실패가 검증됨
* [ ] Fail Closed 동작이 검증됨
* [ ] 관련 테스트가 모두 통과함
* [ ] 기존 Contract와 구현이 일치함
* [ ] Architecture 및 ADR과 충돌하지 않음
* [ ] Feature Spec과 구현의 차이 또는 차이 없음이 기록됨
* [ ] 실행하지 못한 검증 항목이 기록됨

## 미결정 사항

`Approved`로 변경하기 전에 구현 방향에 영향을 주는 미결정 사항을 해소한다. 결정이 상위 설계를 바꾸면 관련 ADR, Architecture 또는 Contract를 먼저 수정한다.

* ...

## 검증 기록

`Verified`로 변경할 때 실제 명령과 결과를 작성한다.

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 관련 테스트 | `...` | 미실행 |
| 문서 링크 | `...` | 미실행 |
| 기본 포맷 | `git diff --check` | 미실행 |

실행하지 못한 검증과 남은 위험:

* ...
