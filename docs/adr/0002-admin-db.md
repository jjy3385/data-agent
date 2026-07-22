# 0002. 관리 데이터베이스 (Admin Database)

## 상태 (Status)

승인됨 (Accepted)

## 배경 (Context)

시스템은 대상 업무 데이터베이스를 변경하지 않으면서 사용자, 접근 정책, 감사 로그
(Audit Log) 및 오류 신고를 저장할 내부 저장소가 필요하다.

MVP는 FastAPI 워커 하나로 실행하며 관리 데이터의 크기와 동시 쓰기 규모가 작다. AWS
데모 배포까지는 별도 관리형 데이터베이스를 운영하는 복잡성보다 설치와 테스트가 단순한
로컬 저장소가 적합하다. 다만 컨테이너의 일시적 파일시스템에 관리 데이터를 저장하면
재배포 시 데이터가 사라지고, 여러 인스턴스가 하나의 파일을 공유하면 SQLite의 단일 호스트
전제와 충돌한다.

Admin DB는 대상 DB 실행 경계와 책임이 다르다. 대상 AdventureWorks2022 접근은 승인된
MCP Tool을 통해야 하지만, 애플리케이션 자체의 사용자·정책·감사 데이터는 FastAPI가
별도의 Admin DB를 통해 관리해야 한다.

## 고려한 대안 (Alternatives Considered)

### A. 대상 업무 데이터베이스에 관리 테이블 추가

배포할 데이터베이스 수는 줄지만 대상 업무 DB를 변경하고 업무 데이터와 Governance 기록의
권한 및 Lifecycle이 결합된다. 대상 DB Read-Only 원칙과 관리 데이터 격리 목적에 어긋나므로
채택하지 않았다.

### B. MVP부터 PostgreSQL 또는 관리형 RDS 사용

다중 인스턴스, 동시 쓰기와 운영 가용성에는 유리하지만 MVP와 단일 인스턴스 데모에 별도
서비스, 자격 증명, 네트워크 및 운영 비용을 추가한다. 현재 검증하려는 핵심 경계가 아니므로
MVP에서는 채택하지 않았다.

### C. 컨테이너 일시적 저장소의 SQLite 사용

구성은 가장 단순하지만 컨테이너 교체와 재배포 후 관리 데이터 보존을 보장하지 못한다.
감사 및 오류 신고 기록의 연속성을 잃으므로 채택하지 않았다.

### D. 동일 EC2의 Docker PostgreSQL 사용

로컬과 AWS 데모에서 PostgreSQL Engine을 동일하게 유지하고 향후 RDS로 전환하기 쉽다는
장점이 있다. 그러나 단일 EC2의 EBS에 데이터를 저장하면 SQLite와 마찬가지로 해당 호스트의
가용성과 Storage Lifecycle에 의존한다. RDS의 관리형 백업과 장애 복구 이점은 얻지 못하면서
별도 DB Process, Container, 자격 증명, Port, 자원 사용과 백업 관리가 추가된다.

MVP는 FastAPI 인스턴스와 워커가 각각 하나이고 Admin DB의 데이터 규모와 동시 쓰기가 작다.
Admin DB 제품 자체가 데모의 검증 대상도 아니므로, 향후 전환 편의보다 데모까지의 설치·실행·
운영 단순성을 우선하여 채택하지 않았다.

## 결정 (Decision)

애플리케이션 메타데이터 (Metadata)와 거버넌스 (Governance) 기록을 위해 별도의
관리 데이터베이스 (Admin DB)를 사용한다.

MVP와 AWS 데모에서는 다음 규칙으로 SQLite를 사용한다.

이 결정의 우선 기준은 로컬 개발뿐 아니라 단일 EC2 기반 AWS 데모까지 필요한 전체 구성을
가장 단순하게 유지하는 것이다. 운영형 고가용성이나 수평 확장을 미리 구현하기 위해 MVP에
별도 DB Server를 추가하지 않는다.

1. Admin DB 파일 위치는 배포 환경별 설정으로 지정한다.
2. 배포 시 SQLite 파일은 애플리케이션 이미지나 컨테이너의 일시적 저장소가 아니라 단일
   호스트에 로컬 Block Storage로 마운트된 영속 위치에 저장한다.
3. FastAPI 인스턴스와 워커는 각각 하나만 사용한다. 여러 프로세스나 호스트가 하나의 SQLite
   파일을 공유하는 구성과 수평 확장은 지원하지 않는다.
4. Admin DB를 열 수 없거나 필요한 Schema를 준비할 수 없으면 애플리케이션 시작을 중단한다
   (Fail Closed).
5. Admin DB 접근 책임을 별도 경계에 두어 이후 운영 요구사항이 생기면 PostgreSQL 또는
   관리형 데이터베이스로 전환할 수 있게 한다.
6. Admin DB 접근은 대상 DB용 MCP 실행 경계를 통하지 않는다. 이 예외는 FastAPI가 대상
   AdventureWorks2022에 직접 접근할 수 있다는 의미가 아니다.

## 결과 (Consequences)

* 관리 데이터는 대상 업무 데이터와 격리되고 대상 DB의 Read-Only 원칙을 유지한다.
* 로컬 개발, 자동 테스트와 단일 인스턴스 AWS 데모에서 별도 DB Server 없이 같은 Admin DB
  구성을 사용할 수 있다.
* 배포 환경은 SQLite 파일을 보존할 영속 Block Storage, 파일 권한과 백업을 관리해야 한다.
* 감사 및 오류 신고 Workflow는 Admin DB 가용성에 의존하며 준비 실패 시 애플리케이션을
  시작할 수 없다.
* 단일 호스트와 단일 애플리케이션 인스턴스 제약 때문에 수평 확장과 고가용성을 제공하지
  않는다.
* 운영 환경에서 동시성, 가용성 또는 다중 인스턴스가 필요해지면 별도 ADR과 데이터 Migration을
  통해 Admin DB 제품과 배포 구조를 변경해야 한다.

## 관련 문서

* [FEAT-0002 Admin DB 기반 Spec](../features/0002-admin-db-foundation/spec.md)
* [컴포넌트 책임과 경계](../architecture/component-boundaries.md)
* [프로젝트 모듈 구조](../architecture/project-structure.md)
* [ADR 0007 대상 DB 실행을 위한 로컬 stdio MCP 경계](0007-local-stdio-mcp-db-boundary.md)
