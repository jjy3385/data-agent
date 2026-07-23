# 계약 문서 안내 (Contracts)

> 이 폴더는 구성요소 사이에 전달되는 데이터의 형식과 불변조건을 정의한다. 필드명, 타입, 허용값 또는 오류 처리가 궁금할 때 이곳을 확인한다.

## 계약 목록

| 계약 | 설명 |
|---|---|
| [RuntimeIntent](runtime-intent.md) | 자연어 질문을 Metadata 검색 입력으로 구조화한 계약 |
| [QueryPlan](query-plan.md) | 자연어와 SQL 사이의 검증 가능한 실행 계획 계약 |
| [`inspect_schema`](inspect-schema.md) | AdventureWorks2022의 사용자 정의 Physical Schema를 읽기 전용으로 수집하는 MCP Tool 입출력 계약 |
| [`execute_readonly_query`](execute-readonly-query.md) | 검증 완료 SQL을 실행하는 MCP Tool 입출력 계약 |
| [XAI Payload](xai-payload.md) | 최종 설명 생성에 사용할 근거 데이터 계약 |
| [Result Context](result-context.md) | MVP Direct 전달과 Post-MVP Handle 전달 계약 |

## 읽는 방법

Contract는 현재 시스템이 따라야 하는 정확한 경계를 설명한다. 왜 이 구조를 선택했는지는 [ADR](../adr/)을, 구성요소가 Contract를 어떤 순서로 주고받는지는 [아키텍처 문서](../architecture/)를 참고한다.
