# 0002. 관리 데이터베이스 (Admin Database)

## 상태 (Status)

제안됨 (Proposed)

## 배경 (Context)

시스템은 대상 업무 데이터베이스를 변경하지 않으면서 사용자, 접근 정책, 감사 로그
(Audit Log) 및 오류 신고를 저장할 내부 저장소가 필요하다.

## 결정 (Decision)

애플리케이션 메타데이터 (Metadata)와 거버넌스 (Governance) 기록을 위해 별도의
관리 데이터베이스
(Admin DB)를 사용한다.

## 결과 (Consequences)

- 관리 데이터는 대상 업무 데이터와 격리된다.
- MVP는 SQLite로 시작하고, 운영 요구사항이 변경되면 이후 확장할 수 있다.
- 감사 및 오류 신고 워크플로 (Workflow)는 Admin DB 가용성에 의존한다.
