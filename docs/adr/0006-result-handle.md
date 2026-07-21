# 0006. Post-MVP LLM 배포 모드별 결과 전달 전략

## 상태 (Status)

MVP 결정 승인 / Post-MVP 전략 제안 (Accepted for MVP / Proposed for Post-MVP)

## 배경 (Context)

MVP는 AdventureWorks2022 데모 데이터를 사용하며 최대 2-Depth Workflow를 검증한다. Depth 2의 다음 행동을 결정하려면 LLM이 Depth 1 실행 결과를 확인할 수 있어야 한다.

MVP 단계에서 Result Store, Result Handle 발급·해석(Resolve), TTL 및 Workflow Scope 검사를 모두 구현하면 핵심 Workflow 검증보다 상태 관리 구현의 비중이 커진다. 따라서 MVP에서는 LLM Provider나 배포 형태와 관계없이 행·컬럼 제한이 적용된 앞 단계 결과를 LLM에 직접 전달한다.

Post-MVP에서는 LLM 배포 형태에 따라 결과 전달 경로를 선택할 필요가 있다. 조직이 통제하는 Private LLM은 MVP의 직접 전달 경로를 계속 사용할 수 있다. 외부 Hosted LLM을 사용하는 External 모드에서는 원본 결과를 Backend에 유지하고 불투명한 Result Handle과 제한된 Summary 또는 Projection만 LLM에 전달하는 별도 경로를 제공한다.

Result Handle은 데이터 전달 형식이나 권한 자체가 아니라 Backend Result Store의 결과를 현재 Workflow 안에서 다시 찾기 위한 수명이 짧은 참조다.

## 고려한 대안 (Alternatives Considered)

### A. MVP부터 모든 LLM에 Result Handle 적용

하나의 결과 전달 경로만 유지할 수 있지만 Result Store, TTL, Handle Scope, Resolve와 Audit을 MVP에서 모두 구현해야 한다. 4주 MVP의 핵심인 Text-to-SQL과 2-Depth Workflow 검증 범위를 키우므로 채택하지 않는다.

### B. Post-MVP에서도 모든 LLM에 결과 직접 전달

구조는 단순하지만 외부 LLM을 사용할 때 Backend가 보유한 원본 결과와 LLM에 제공할 최소 데이터의 경계를 명시적으로 분리하기 어렵다. External 모드의 확장 경로로 채택하지 않는다.

### C. Post-MVP 배포 모드별 전달 경로 분기

Private 모드는 MVP의 직접 전달 경로를 재사용하고 External 모드만 Result Handle 경로를 사용한다. 두 경로를 테스트해야 하지만 배포 특성에 맞는 복잡도를 선택할 수 있으므로 채택한다.

## 결정 (Decision)

### MVP

1. Result Store, Result Handle 발급과 Handle Resolve를 구현하지 않는다.
2. LLM Provider와 배포 형태를 결과 전달 경로의 분기 조건으로 사용하지 않는다.
3. Depth 2 판단에는 TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 앞 단계 결과를 LLM에 직접 전달한다. 제한 없는 Raw Result를 전달한다는 의미는 아니다.
4. LLM은 `STOP`, `DRILL_DOWN`, `ASK_CLARIFICATION` 중 허용된 다음 행동만 제안한다.
5. 실제 Depth 2 대상과 PK는 Backend가 Depth 1 결과 범위 안에서 선택한다.

### Post-MVP

1. LLM Provider와 배포 모드를 분리하여 설정한다. Provider는 모델 호출 구현을 선택하고 `LLM_DEPLOYMENT_MODE`는 결과 전달 정책을 선택한다.
2. `LLM_DEPLOYMENT_MODE=private`는 MVP와 동일하게 제한된 앞 단계 결과를 LLM에 직접 전달한다.
3. `LLM_DEPLOYMENT_MODE=external`은 Raw Result를 Backend Result Store에 보관하고 LLM에는 불투명한 Result Handle과 필요한 최소 Summary 또는 Projection만 전달한다.
4. 지원하지 않는 배포 모드이거나 필요한 Result Handle 구성요소가 준비되지 않으면 Fail Closed 처리한다.
5. 두 모드 모두 LLM의 다음 행동을 Backend가 검증하고 실제 Depth 2 대상은 Backend가 선택한다.

### External 모드 Result Handle 불변조건

1. Backend만 Handle을 해석할 수 있다. LLM이나 Slack Client는 Handle로 데이터를 직접 조회할 수 없다.
2. Handle은 데이터, SQL 또는 실행 권한으로 취급하지 않는다.
3. Handle Resolve 시 현재 ACL, Correlation ID, Workflow Depth, 허용된 다음 행동과 TTL을 다시 검사한다.
4. Handle은 활성 Workflow 안에서만 유효하며 요청 간에 임의로 재사용할 수 없다.
5. Raw Result, Result Summary와 LLM Projection을 분리하여 저장하고 관리한다.
6. LLM에는 Handle과 현재 판단에 필요한 최소 Summary 또는 Projection만 전달한다.
7. Handle 발급, Resolve 시도, 거부, 만료와 삭제를 감사(Audit)한다.

## 결과 (Consequences)

* MVP는 별도 Result Store 없이 2-Depth Workflow의 핵심 동작을 먼저 검증할 수 있다.
* MVP에서 사용하는 LLM Provider나 배포 형태가 바뀌어도 결과 전달 흐름은 동일하다.
* Post-MVP Private 모드는 MVP의 직접 전달 구현을 재사용한다.
* Post-MVP External 모드는 Result Store, Handle Lifecycle, Resolve, TTL, Scope와 Audit 구현이 추가로 필요하다.
* Post-MVP에는 Direct와 Handle 두 결과 전달 경로에 대한 별도 Contract와 E2E 테스트가 필요하다.
* Result Handle만으로 LLM이 임의 SQL을 실행하거나 Workflow 범위를 확장할 수 없다.

## 관련 문서

* [Result Context Contract](../contracts/result-context.md)
* [XAI Payload Contract](../contracts/xai-payload.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP 범위](../mvp/scope.md)
