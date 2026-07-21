# Feature Tasks 템플릿

> Tasks는 Approved Spec과 Plan을 실행 가능한 순서로 나눈다. 새로운 요구사항이나 설계를 Tasks에서 만들지 않으며 `Approved` 전에는 구현을 시작하지 않는다.

# `<Feature Name>` Tasks

* Feature ID: `FEAT-NNNN`
* Status: `Draft`
* Source Spec: `<relative-link>` (`Approved`)
* Source Plan: `<relative-link>` (`Approved`)

## 실행 원칙

* 선행 Task와 의존 순서를 지킨다.
* AI Agent에는 한 번에 하나의 검토 가능한 Task만 요청한다.
* 코드 동작과 해당 테스트 또는 재현 가능한 검증을 같은 Task에 포함한다.
* 범위 밖 리팩터링, 파일 이동과 의존성 추가를 하지 않는다.

## 요구사항 Coverage

| Spec 요구사항 | Plan 절 | 구현 Task | 검증 Task |
|---|---|---|---|
| `FR-001` | ... | `TASK-001` | `TASK-001` |

## 작업 순서와 의존성

```text
TASK-001 → TASK-002 → TASK-003
```

## `TASK-001` `<Task Name>`

* Status: `Pending`
* 요구사항: `FR-...`
* 선행 Task: 없음
* 대상 파일:
  * `...`

구현:

* ...

테스트 또는 검증:

* ...

완료 조건:

* [ ] 구현 범위 충족
* [ ] 관련 정상·실패 테스트 통과
* [ ] 실제 실행 명령과 결과 기록
* [ ] Spec·Plan과 차이 또는 차이 없음 기록

실행 및 검토 기록:

* 실행 명령: 미실행
* 결과: 미실행
* Reviewer 의견과 처리: 미검토

## Feature 전체 검증

* [ ] 모든 Spec 요구사항이 완료된 Task에 연결됨
* [ ] 모든 Plan 설계가 구현 또는 명시적으로 제외됨
* [ ] 전체 자동 테스트 통과
* [ ] 필요한 수동 검증 완료
* [ ] 실행하지 못한 검증과 남은 위험 기록
* [ ] Codex와 Gemini 구현 검토 완료

## 최종 구현 검토

| Reviewer | 발견 사항 | 심각도 | 처리 Task 또는 기각 근거 | 상태 |
|---|---|---|---|---|
| Codex | ... | High/Medium/Low | ... | Open/Resolved/Rejected |
| Gemini | ... | High/Medium/Low | ... | Open/Resolved/Rejected |

## 최종 검증 기록

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 관련 테스트 | `...` | 미실행 |
| 수동 검증 | `...` | 미실행 |
| 문서 링크 | 저장소 내부 상대 링크 검사 | 미실행 |
| 기본 포맷 | `git diff --check` | 미실행 |

실행하지 못한 검증과 남은 위험:

* ...
