# 3주 MVP 로드맵 (MVP Roadmap)

> 이 문서는 현재 개발 위치와 다음 구현 순서를 관리한다. 작업을 시작하거나 우선순위를 바꿀 때 이 체크리스트를 먼저 갱신한다.

## 현재 방향

MVP는 먼저 자연어 질문이 실제 데이터 조회 결과까지 이어지는 Walking Skeleton을 완성한다. 이후 정책과 안전 경계를 적용해 AWS에 배포하고, 마지막으로 Depth 2와 XAI를 연결한다.

## Week 1: Local Depth 1 Demo

* [x] FEAT-0001 FastAPI 프로젝트 기본 구조
  * Feature: [FEAT-0001 FastAPI 프로젝트 기본 구조 명세](../features/0001-fastapi-bootstrap/spec.md)

* [x] FEAT-0002 관리 DB 기반
  * Feature: [FEAT-0002 관리 DB 기반 명세](../features/0002-admin-db-foundation/spec.md)
  * 사용자·역할·Table Policy·Audit을 위한 SQLite 기반 Admin DB 구성

* [x] FEAT-0003 MCP 읽기 전용 데이터 접근
  * Feature: [FEAT-0003 MCP 읽기 전용 데이터 접근 명세](../features/0003-mcp-readonly-data-access/spec.md)
  * AdventureWorks2022 전용 Read-Only MCP 연결
  * Schema Inspection과 Physical Metadata 구성
  * 제한된 Read-Only Query 실행

* [ ] FEAT-0004 자연어 질문 처리 최소 동작 흐름 (Walking Skeleton)
  * 대표 재고 질문 하나를 처리하는 자연어 질문 API
  * 최소 Business Metadata, RuntimeIntent와 QueryPlan
  * LLM SQL 생성부터 Bounded Result 반환까지 연결

* [ ] FEAT-0005 Jinja2 기반 데모 웹 UI
  * 자연어 질문 입력과 조회 결과 표시
  * Business·Physical Metadata 읽기 전용 조회
  * 승인된 AdventureWorks Sample 데이터 조회

## Week 2: Safe Deployed Depth 1

* [ ] FEAT-0006 정책 통제 및 안전한 실패 경계
  * 사용자·역할·Table Policy 기반 ACL 적용
  * RuntimeIntent·QueryPlan·SQL 검증과 Guardrail
  * 주요 실패 처리와 기본 Audit 연결

* [ ] FEAT-0007 AWS 데모 배포
  * 단일 EC2와 EBS 기반 데모 환경 구성
  * FastAPI, 로컬 `stdio` MCP와 AdventureWorks 연결
  * 데모 웹 UI 배포와 Depth 1 Smoke Test

## Week 3: Depth 2 & XAI

* [ ] FEAT-0008 승인된 공급 위험 메타데이터 카탈로그
  * 대표 공급 위험 질문에 필요한 Business Metadata 확장 및 승인
  * Sales·Production·Purchasing 영역 연결

* [ ] FEAT-0009 2단계 질문 처리 흐름 (Depth 2 Workflow)
  * Depth 1 결과를 기반으로 추가 조회 대상 선택
  * 최대 Depth 2 QueryPlan·SQL 생성과 안전한 실행
  * 대표 공급 위험 질문 End-to-End 처리

* [ ] FEAT-0010 설명 가능한 최종 응답 (XAI)
  * 실제 실행 근거를 이용한 설명 가능한 응답 생성
  * 조회 기준·제한과 자연어 설명을 데모 웹 UI에 표시
  * AWS 환경 최종 End-to-End 검증

## Post-MVP

* Slack 연동
* SQL Self-Healing
* 다중 LLM Provider 전환 검증
* Metadata·사용자·정책 편집 UI
* 범용 Data Explorer와 임의 SQL Console
* 추가 업무 시나리오
* Error Report 관리 Workflow와 UI
* CI/CD와 IaC
* 다중 인스턴스 운영 구성

## 관련 문서

* [MVP 범위](scope.md)
* [MVP 완료 기준](acceptance-criteria.md)
* [개발 프로토콜](../development-protocol.md)
