# 아키텍처 문서 안내 (Architecture)

> 이 폴더는 시스템 구성요소가 어떻게 연결되고 요청이 어떤 순서로 흐르는지 설명한다. 전체 그림이 필요하면 `overview.md`에서 시작한다.

## 문서 목록

| 문서 | 답하는 질문 |
|---|---|
| [전체 아키텍처](overview.md) | 시스템 전체는 어떤 구성요소로 이루어지는가? |
| [컴포넌트 경계](component-boundaries.md) | FastAPI, MCP Client Manager와 MCP Server의 책임은 무엇인가? |
| [질문 처리 시퀀스](query-execution-sequence.md) | HTTP 자연어 질문부터 최종 응답까지 어떤 순서로 처리하는가? |
| [프로젝트 구조](project-structure.md) | 각 책임을 어느 모듈에 구현하는가? |

## 문서 경계

아키텍처 문서는 연결 관계와 책임을 설명한다. 정확한 필드 형식은 [Contract](../contracts/)를, 선택 이유와 대안은 [ADR](../adr/)을 참고한다.
