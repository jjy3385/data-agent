# 결과 컨텍스트 전달 계약 (Result Context Contract)

> 이 문서는 Depth 2 판단을 위해 앞 단계 실행 결과를 LLM에 제공하는 방식을 정의한다. MVP의 Direct 전달과 Post-MVP의 배포 모드별 Direct·Handle 경로를 구분한다.

## 이 문서를 읽는 이유

* MVP에서 LLM에 어떤 결과를 직접 전달하는지 확인한다.
* Bounded Result와 제한 없는 Raw Result를 구분한다.
* Post-MVP Private·External 모드의 결과 전달 차이를 확인한다.

## 용어

| 용어 | 의미 |
|---|---|
| Bounded Result | TOP N, 허용 컬럼과 Maximum Returned Rows가 적용된 앞 단계 실행 결과 |
| Direct | Result Handle 없이 Bounded Result를 LLM에 직접 전달하는 경로 |
| Projection | External 모드에서 LLM의 현재 판단에 필요한 최소 부분 결과 또는 요약 |
| Result Handle | Backend Result Store의 결과를 현재 Workflow 안에서 참조하는 불투명 식별자 |

## MVP Direct 전달

* Result Store, Result Handle 발급과 Handle Resolve를 구현하지 않는다.
* LLM Provider나 배포 형태에 따라 결과 전달 경로를 분기하지 않는다.
* Depth 2 판단에는 Bounded Result를 LLM에 직접 전달한다.
* Direct 전달은 제한 없는 DB Raw Result를 전달한다는 의미가 아니다.
* LLM Next Action은 `STOP`, `DRILL_DOWN`, `ASK_CLARIFICATION` 중 하나로 제한한다.
* 실제 Depth 2 대상과 PK는 Backend가 Depth 1 Bounded Result 안에서 선택한다.
* LLM은 Depth 1 범위 밖 대상을 추가할 수 없다.

## Post-MVP 배포 모드별 전달

### Private 모드

`LLM_DEPLOYMENT_MODE=private`는 MVP와 같은 Direct 경로를 사용한다. Bounded Result를 Result Handle 없이 LLM에 전달한다.

### External 모드

`LLM_DEPLOYMENT_MODE=external`은 실행 결과를 Backend Result Store에 보관한다. LLM에는 불투명한 Result Handle과 현재 판단에 필요한 최소 Summary 또는 Projection만 전달한다.

Backend는 Handle Resolve 시 ACL, Correlation ID, Workflow Depth, 허용된 다음 행동과 TTL을 다시 검사한다. LLM이나 입력 채널 Client는 Handle로 결과를 직접 조회할 수 없다.

## 공통 불변조건

* 어떤 모드에서도 LLM이 SQL 실행 권한이나 대상 선택 최종 권한을 갖지 않는다.
* 실제 Depth 2 대상은 Backend가 앞 단계 결과 범위 안에서 선택한다.
* 결과 전달 방식과 관계없이 Correlation ID 기반 Audit을 유지한다.

## 관련 문서

* [ADR 0006: Post-MVP LLM 배포 모드별 결과 전달 전략](../adr/0006-result-handle.md)
* [XAI Payload Contract](xai-payload.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
