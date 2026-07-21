# 기능 명세 안내 (Feature Specifications)

> 이 디렉터리는 MVP 로드맵의 큰 구현 항목을 실제 코드와 테스트로 연결한다. 기능 하나의 범위, 공개 경계, 관찰 가능한 동작과 완료 조건을 정하되 ADR, Architecture와 Contract의 내용을 복사하지 않는다.

## Feature Specification의 역할

Feature Specification은 "이번 기능에서 무엇을 구현하고 어떻게 검증할 것인가"를 정의한다. 프로젝트 전체 방향은 루트 `README.md`, 구현 순서는 MVP Roadmap, 설계 이유는 ADR, 구성요소 책임은 Architecture, 정확한 데이터 형식은 Contract를 기준으로 한다.

전체 작업 관계는 다음과 같다.

```text
MVP Roadmap의 책임 단위
  → Feature Specification
  → 작고 검토 가능한 구현 Task
  → 코드와 해당 테스트
  → Feature 전체 검증
```

Feature Specification이 있더라도 AI Agent에게 Feature 전체를 한 번에 구현하도록 요청하지 않는다.

## 작성 대상

다음 조건 중 하나 이상에 해당하면 Feature Specification을 작성한다.

* 여러 파일을 수정하는 기능
* 공개 Interface 또는 Contract에 영향을 주는 기능
* 권한, 보안 또는 Fail Closed 경계를 다루는 기능
* Lifecycle이나 상태 전이가 있는 기능
* 여러 정상·실패 경로를 검증해야 하는 기능
* 나중에 구현 의도를 복원할 필요가 있는 기능

작은 Private Helper 함수, 단순 리팩터링, 테스트 하나 추가와 오타 수정에는 별도 Feature Specification을 작성하지 않는다.

## 상태

| 상태 | 의미 | 다음 상태로 이동하는 조건 |
|---|---|---|
| `Draft` | 요구사항, 범위와 미결정 사항을 검토 중 | 공개 경계, 실패 동작과 완료 조건이 합의됨 |
| `Approved` | 구현 가능한 명세로 확정됨 | 첫 구현 Task를 시작함 |
| `In Progress` | 하나 이상의 Task를 구현·검증 중 | 모든 Task와 Feature 전체 검증이 끝남 |
| `Verified` | 구현, 테스트와 기준 문서의 일치가 확인됨 | 최종 상태 |

상태만으로 완료를 선언하지 않는다. `Verified`로 변경할 때 Feature 문서의 검증 기록에 실행한 명령, 결과와 실행하지 못한 검증을 남긴다.

## 작성 원칙

* 관련 ADR, Architecture, Contract와 MVP 문서를 링크하고 같은 규칙을 반복해서 복사하지 않는다.
* 모듈 책임, 공개 Class·Protocol·Function·Method, 입력·반환 타입, 오류 형식과 관찰 가능한 동작을 명확히 한다.
* Private Helper, 로컬 변수명과 외부 동작에 영향을 주지 않는 내부 구현은 미리 고정하지 않는다.
* 포함 범위뿐 아니라 제외 범위를 명시하여 작업이 다른 책임으로 확장되지 않게 한다.
* 구현 Task는 코드 동작과 그 동작의 테스트를 함께 다루도록 나눈다. 설정처럼 테스트가 적합하지 않은 작업은 재현 가능한 검증 명령을 같은 Task에 포함한다.
* Feature Spec과 기준 문서가 충돌하면 구현을 시작하지 않고 충돌 위치와 영향을 먼저 확인한다.
* 구현 중 명세 변경이 필요하면 코드를 기준으로 문서를 사후 수정하지 않는다. 변경 이유를 검토하고 Feature Spec 또는 상위 기준 문서를 먼저 승인한다.

## 파일 이름과 식별자

파일 이름은 `NNNN-kebab-case.md` 형식을 사용한다. 디렉터리가 분리되어 있으므로 ADR 번호와 같아도 서로 다른 식별자다. 문서 제목 아래에는 `FEAT-NNNN` 식별자를 표시한다.

## Feature 목록

| Feature | 상태 | Roadmap 책임 |
|---|---|---|
| [FEAT-0001 FastAPI Bootstrap](0001-fastapi-bootstrap.md) | `Draft` | Week 1 FastAPI 프로젝트 기본 구조 |

## 관련 문서

* [프로젝트 문서 안내](../README.md)
* [AI-Assisted Development Protocol](../development-protocol.md)
* [MVP Roadmap](../mvp/roadmap.md)
* [Feature Specification Template](template.md)
