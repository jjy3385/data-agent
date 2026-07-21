# 0001. 대상 데이터베이스 읽기 전용 접근 (Read-Only Target Database Access)

## 상태 (Status)

제안됨 (Proposed)

## 배경 (Context)

에이전트 (Agent)는 생성된 SQL을 사용해 기업 데이터 소스에 질의한다. 대상 데이터베이스
(Target Database)는 데이터 변경, 우발적인 쓰기 및 안전하지 않은 실행 경로로부터
보호되어야 한다.

## 결정 (Decision)

대상 데이터베이스 접근은 기본적으로 읽기 전용 (Read-Only)으로 제한한다.

## 결과 (Consequences)

- 애플리케이션 자격 증명에는 대상 데이터베이스 쓰기 권한을 부여하지 않는다.
- 생성된 SQL은 실행 전에 가드레일 (Guardrail)을 통과해야 한다.
- 쿼리 안전성이 불확실하면 반드시 차단한다 (Fail Closed).
