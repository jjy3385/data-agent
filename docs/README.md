# 프로젝트 문서 안내

> 이 문서는 프로젝트의 상세 문서를 찾기 위한 한국어 문서 지도다. 무엇을 읽어야 할지 헷갈릴 때 이 문서에서 시작한다.

## 가장 먼저 읽을 문서

1. [루트 README](../README.md): 프로젝트 철학, 목표, 핵심 원칙과 전체 구조
2. [전체 아키텍처](architecture/overview.md): 시스템 구성요소와 데이터 흐름
3. [MVP 범위](mvp/scope.md): 현재 구현하는 것과 구현하지 않는 것
4. [MVP 로드맵](mvp/roadmap.md): 현재 위치와 다음 작업
5. [MVP 완료 기준](mvp/acceptance-criteria.md): 완료 여부를 판단하는 조건

## 문서 종류

| 궁금한 내용 | 위치 | 문서의 역할 |
|---|---|---|
| 왜 특정 설계를 선택했는가? | [ADR](adr/README.md) | 중요한 설계 결정, 대안과 결과 |
| 정확한 입출력 형식은 무엇인가? | [Contract](contracts/README.md) | RuntimeIntent, QueryPlan, Tool, XAI 계약 |
| 구성요소가 어떻게 연결되는가? | [Architecture](architecture/README.md) | 컴포넌트 책임, 시퀀스와 프로젝트 구조 |
| MVP에서 어디까지 만드는가? | [MVP](mvp/README.md) | 범위, 로드맵과 완료 기준 |
| 테스트 DB 구조는 무엇인가? | [Data](data/README.md) | AdventureWorks2022 스키마 참고 자료 |
| AI와 어떻게 개발하는가? | [개발 프로토콜](development-protocol.md) | 작업 단위와 검토 절차 |

## 문서 작성 원칙

* 한글 설명을 먼저 작성하고 영어 기술 용어는 필요한 경우 병기한다.
* 문서 상단만 읽어도 목적, 범위와 관련 문서를 파악할 수 있어야 한다.
* ADR은 결정 이유, Contract는 정확한 형식, Architecture는 연결 관계를 담당한다.
* 같은 규칙을 여러 문서에 복사하지 않고 기준 문서를 링크한다.
* 구현과 문서가 다르면 안전을 위해 Fail Closed하고 문서를 먼저 정정한다.
