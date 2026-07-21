# 제한된 결과 계약 (Result Projection Contract)

> 이 문서는 대상 DB의 Raw Result와 LLM에 전달하는 최소 Result Projection을 분리하기 위한 MVP 규칙을 정의한다.

## 이 문서를 읽는 이유

* LLM에 전체 조회 결과를 반복 전송하지 않도록 한다.
* Depth 2 판단에 필요한 최소 데이터만 제공한다.
* Raw Result가 현재 Workflow 밖으로 확산되는 것을 막는다.

## MVP 규칙

* Raw Result는 현재 Workflow의 Backend 실행 상태 안에서만 유지한다.
* Backend가 TOP N, 허용 컬럼, 민감정보 정책과 현재 작업 목적을 적용한다.
* Private LLM에는 Result Summary와 최소 Projection만 전달한다.
* LLM Next Action은 `STOP`, `DRILL_DOWN`, `ASK_CLARIFICATION` 중 하나로 제한한다.
* Depth 2의 실제 대상과 PK는 Backend가 Depth 1 Raw Result 안에서 선택한다.
* LLM은 Depth 1 범위 밖 대상을 추가할 수 없다.

## Post-MVP

Public LLM 지원 시에는 불투명한 Result Handle, TTL, Workflow Scope와 재사용 시 ACL 검사를 추가한다. 상세 결정은 [ADR 0006](../adr/0006-result-handle.md)을 따른다.

## 관련 문서

* [XAI Payload Contract](xai-payload.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
