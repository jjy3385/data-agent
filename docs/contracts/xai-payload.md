# 설명 근거 계약 (XAI Payload Contract)

> 이 문서는 최종 사용자 설명을 생성할 때 LLM에 제공할 수 있는 검증된 근거의 범위를 정의한다. XAI 설명은 실제 실행 사실을 벗어나 새로운 계산식이나 판단 근거를 만들 수 없다.

## 상태

초안 (Proposed). 최종 필드 Schema는 Week 3 구현에서 확정한다.

## 이 문서를 읽는 이유

* 최종 설명에 사용할 수 있는 근거를 확인한다.
* 사용자가 확인할 기간, 계산식과 데이터 한계를 누락하지 않도록 한다.
* LLM이 실행되지 않은 사실을 설명에 추가하지 못하게 한다.

## 범위

MVP XAI Payload에는 최소한 다음 논리 정보가 포함된다.

* 사용자 질문과 Correlation ID
* 실제 사용한 승인 Metadata와 QueryPlan
* 실제 실행한 SQL 또는 안전하게 표시한 SQL 요약
* 적용한 기간, 계산식, 단위와 기본값
* 도메인별 데이터 기준일
* 제한된 Result Summary
* `truncated` 여부와 결과 한계
* 실행 오류, 재시도 여부와 Self-Healing 횟수

## 불변조건

* Backend가 실제 Plan, Metadata, SQL과 실행 결과로 Payload를 구성한다.
* LLM은 Payload 범위 안에서만 자연어 설명을 작성한다.
* 승인되지 않은 공식, 데이터 기준일 또는 인과관계를 새로 만들지 않는다.
* `ProductInventory`를 일별 스냅샷으로 오해해 “최신 재고 스냅샷”이라고 단정하지 않는다.

## 관련 문서

* [Result Projection Contract](result-projection.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP 완료 기준](../mvp/acceptance-criteria.md)
