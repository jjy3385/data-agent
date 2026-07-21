# Feature Tasks 템플릿

> Tasks는 Approved Spec과 Plan을 실행 가능한 순서로 나눈다. 새로운 요구사항이나 설계를 Tasks에서 만들지 않으며 `Approved` 전에는 구현을 시작하지 않는다.

# `<Feature Name>` Tasks

* Feature ID: `FEAT-NNNN`
* Status: `Draft`
* Development Track: `<Source Spec과 동일>`
* Source Spec: `<relative-link>` (`Approved`)
* Source Plan: `<relative-link>` (`Approved`)

## Track별 작성 규칙

* `Lightweight`: 요구사항 Coverage, Task 순서와 각 Task의 상태·대상 파일·구현·검증·결과만 기록한다. 공통 완료 조건, 상위 문서 설명과 같은 제약을 Task마다 반복하지 않는다. 일반적으로 3~5개의 검토 가능한 Task로 유지한다.
* `Standard`: Task별 선행 관계, 정상·실패 검증, 고유 완료 조건과 실행·검토 기록을 위험에 비례해 상세히 작성한다.

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

## Tasks 승인 조건

* [ ] Source Spec에 Development Track이 있으면 해당 Track의 Task 상세도를 적용함
* [ ] 모든 Spec 요구사항과 Plan 설계가 구현·검증 Task에 연결됨
* [ ] 선행 관계와 대상 파일이 명확함
* [ ] 코드 동작과 관련 테스트 또는 검증이 같은 Task에 포함됨

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

완료 조건(Standard 또는 Task 고유 조건이 있을 때만 작성):

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
* [ ] 필수 Codex 구현 검토 완료

## 최종 구현 검토

| Reviewer | 발견 사항 | 심각도 | 처리 Task 또는 기각 근거 | 상태 |
|---|---|---|---|---|
| Codex | ... | High/Medium/Low | ... | Open/Resolved/Rejected |

고위험 구현에서 추가 Reviewer를 사용하는 경우 위 표에 행을 추가한다.

## 최종 검증 기록

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| 관련 테스트 | `...` | 미실행 |
| 수동 검증 | `...` | 미실행 |
| 문서 링크 | 저장소 내부 상대 링크 검사 | 미실행 |
| 기본 포맷 | `git diff --check` | 미실행 |

실행하지 못한 검증과 남은 위험:

* ...
