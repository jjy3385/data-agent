# Admin DB 기반 Spec

> 이 문서는 대상 업무 데이터베이스와 분리된 MVP 관리 데이터베이스의 요구사항과 범위를 정의한다. 구체적인 ORM, Migration 도구, 모듈 배치와 컬럼 타입은 Spec 승인 후 `plan.md`에서 결정한다.

* Feature ID: `FEAT-0002`
* Status: `Approved`
* Development Track: `Standard`
* Track 선택 근거: 사용자·역할과 접근 정책이라는 보안 경계, SQLite Schema 초기화 및 영속 자원 Lifecycle을 포함하므로 Standard Track을 적용한다.
* Roadmap: [Week 1 - Admin DB(SQLite) DDL](../../mvp/roadmap.md#week-1-business-metadata--security-foundation)

## 목적

대상 AdventureWorks2022 데이터베이스를 변경하지 않고 사용자, 역할 기반 테이블·컬럼 접근 정책, 감사 이벤트와 오류 신고를 저장할 별도의 Admin DB 기반을 제공한다.

MVP와 AWS 데모 배포에서는 단일 FastAPI 인스턴스가 영속 저장소에 위치한 SQLite 파일을 사용한다. 이후 Admin DB 제품을 교체하더라도 Workflow와 정책 계층이 SQLite 파일 접근 방식에 직접 결합되지 않도록 관리 DB의 책임 경계를 분명히 한다.

## 범위

포함:

* 대상 업무 DB와 분리된 SQLite Admin DB
* `users`, `table_policies`, `audit_logs`, `error_reports` 관리 데이터 구조
* 사용자 한 명과 역할 하나의 1:1 연결
* 역할·물리 테이블 단위로 명시적인 허용 컬럼 집합을 관리하는 정책 구조
* Correlation ID로 Workflow 실행 단계를 연결하는 이벤트 단위 Audit 구조
* 오류 신고를 원래 실행 또는 Audit 기록과 연결하는 구조
* 반복 실행해도 기존 관리 데이터를 훼손하지 않는 Schema 초기화 기반
* Admin DB 위치를 배포 환경에 맞게 지정할 수 있는 설정
* Admin DB 준비 실패 시 애플리케이션이 정상 상태로 시작하지 않는 실패 동작
* Schema, 관계, 제약 및 초기화 실패에 대한 자동 검증

제외:

* 사용자 가입, 로그인과 완전한 인증 시스템
* 다중 역할, 사용자별 예외 정책과 역할 관리 UI
* 행 단위 정책, 조건식 기반 정책과 명시적 Deny 규칙
* Entity, Dimension, Metric, Time Policy, Join 등 Business Metadata Catalog
* 실제 Metadata Retrieval, ACL 평가와 Context Builder
* 사용자·정책 조회와 Audit·오류 저장을 위한 운영용 Repository 또는 Service
* Workflow 각 단계에서 Audit 이벤트를 생성하는 서비스 통합
* Audit 이벤트의 수정·삭제를 차단하는 Append-Only Writer와 Payload Allowlist·마스킹
* 오류 신고 API와 Slack 오류 신고 흐름
* Audit 보존 기간, 장기 Archive와 운영용 검색·분석 UI
* 다중 FastAPI 인스턴스 또는 여러 호스트가 하나의 SQLite 파일을 공유하는 배포
* PostgreSQL, Amazon RDS 등 운영용 Admin DB로의 전환
* 데모용 사용자와 역할별 ACL 정책의 초기 Seed 데이터
* MCP Server 및 대상 AdventureWorks2022 연결

## 사용자 또는 시스템 시나리오

### 시나리오 1: 애플리케이션이 관리 데이터베이스를 준비한다

* Given: 유효한 Admin DB 설정과 읽기·쓰기 가능한 영속 저장 위치가 준비되어 있다.
* When: 애플리케이션을 처음 시작하거나 동일한 Schema로 다시 시작한다.
* Then: 필요한 관리 데이터 구조가 준비되고 기존 데이터는 유지되며 애플리케이션이 정상 시작한다.

### 시나리오 2: 사용자와 역할의 제약을 표현한다

* Given: Slack 사용자를 Admin DB에 등록한다.
* When: 사용자 데이터의 제약을 검사한다.
* Then: 중복되지 않는 Slack 사용자 식별자, 활성 상태와 `supply_risk_analyst` 또는 `inventory_viewer` 중 정확히 하나의 역할을 표현할 수 있다.

### 시나리오 3: 역할의 테이블·컬럼 허용 범위를 표현한다

* Given: 역할별 Table·Column Policy가 등록되어 있다.
* When: 정책 데이터의 제약을 검사한다.
* Then: 역할·물리 테이블 단위 정책에 명시된 컬럼 집합만 식별할 수 있으며 정책이 없거나 집합에 없는 컬럼은 허용된 것으로 표현되지 않는다.

### 시나리오 4: 하나의 실행에 속한 Audit 이벤트 구조를 표현한다

* Given: 하나의 질문이 여러 Workflow 단계와 최대 Depth 2 실행을 거친다.
* When: 각 단계가 별도의 Audit 이벤트로 저장된다.
* Then: 기존 실행 요약 행을 반복 갱신하지 않고 이벤트 발생 순서, 단계, 결과와 재시도 여부를 하나의 Correlation ID로 연결할 수 있다.

### 시나리오 5: 오류 신고 관계를 표현한다

* Given: 사용자가 특정 실행 결과에 대해 오류를 신고한다.
* When: 오류 신고 데이터의 관계를 검사한다.
* Then: 신고 내용은 원래 실행의 Correlation ID를 필수로 가지며 필요한 경우 같은 실행에 속한 개별 Audit 이벤트를 함께 참조할 수 있다.

### 실패 시나리오 1: Admin DB를 준비할 수 없다

* Given: Admin DB 경로에 접근할 수 없거나 Schema가 호환되지 않거나 초기화에 실패한다.
* When: 애플리케이션 시작을 시도한다.
* Then: 원인을 식별할 수 있는 오류를 남기고 Admin DB가 준비된 것처럼 정상 시작하지 않는다.

### 실패 시나리오 2: 지원하지 않는 역할이 입력된다

* Given: 허용된 MVP 역할이 아닌 값으로 사용자를 저장하려 한다.
* When: 관리 데이터의 유효성을 검사하거나 저장한다.
* Then: 해당 값을 거부하며 무권한 사용자를 기본 역할로 대체하지 않는다.

### 실패 시나리오 3: 중복·미등록 또는 비활성 사용자

* Given: 중복된 Slack 사용자 식별자를 저장하거나 미등록·비활성 사용자의 역할을 사용하려 한다.
* When: 사용자 데이터의 제약을 검사하거나 후속 ACL 계층이 사용자를 식별한다.
* Then: 중복 사용자는 저장하지 않고 미등록·비활성 사용자는 권한이 있는 사용자로 처리하지 않으며 기본 역할로 대체하지 않는다.

### 실패 시나리오 4: 불완전한 정책 또는 Audit 관계가 입력된다

* Given: 대상 역할·물리 테이블·허용 컬럼 집합 또는 Correlation ID 등 필수 식별 정보가 누락되어 있다.
* When: 정책 또는 Audit 관련 데이터를 저장하려 한다.
* Then: 불완전한 데이터를 유효한 정책이나 추적 가능한 실행 기록으로 저장하지 않는다.

## 기능 요구사항

* `FR-001`: 시스템은 대상 AdventureWorks2022 데이터베이스와 분리된 SQLite Admin DB에 관리 데이터를 저장해야 한다.
* `FR-002`: 시스템은 Admin DB의 영속 저장 위치를 배포 환경별 설정으로 지정할 수 있어야 한다.
* `FR-003`: 시스템은 동일한 Schema 초기화를 반복해도 기존 관리 데이터가 삭제되거나 중복 생성되지 않아야 한다.
* `FR-004`: 시스템은 중복되지 않는 Slack 사용자 식별자, 필수 활성 상태와 하나의 역할을 사용자 정보로 관리할 수 있어야 한다.
* `FR-005`: MVP 사용자 역할은 `supply_risk_analyst`와 `inventory_viewer`만 허용해야 하며, 역할 누락이나 알 수 없는 역할을 거부해야 한다.
* `FR-006`: 시스템은 역할과 물리 Schema·Table 조합마다 하나의 정책으로 비어 있지 않은 허용 컬럼 집합을 관리할 수 있어야 한다.
* `FR-007`: Table Policy가 없거나 컬럼이 해당 정책의 허용 집합에 없으면 그 물리 리소스를 허용 상태로 해석할 수 없어야 한다.
* `FR-008`: MVP Table Policy는 Wildcard 또는 컬럼 목록 생략을 통한 전체 컬럼 허용을 지원하지 않아야 하며, 대상 DB에 새로 추가된 컬럼을 자동 허용해서는 안 된다.
* `FR-009`: 시스템은 각 Audit 단계를 별도 이벤트로 저장하고 Correlation ID, Workflow 단계, Depth, 처리 결과와 발생 시각으로 연결할 수 있어야 한다.
* `FR-010`: Audit 구조는 정상 처리뿐 아니라 권한 거부, Contract 오류, Guardrail 거부, Timeout, 연결 종료와 재시도 결과를 구분할 수 있어야 한다.
* `FR-011`: Audit 구조는 후속 이벤트를 기록하기 위해 기존 실행 요약 행을 수정하도록 요구하지 않아야 한다. 운영 중 Audit 이벤트의 수정·삭제 차단은 후속 Audit Writer의 책임이다.
* `FR-012`: 시스템은 오류 신고에 원래 실행의 Correlation ID를 필수로 저장하고, 선택적으로 같은 Correlation ID에 속한 개별 Audit 이벤트를 참조할 수 있어야 한다.
* `FR-013`: Admin DB 설정, Schema, 관계와 제약조건을 자동 테스트로 검증할 수 있어야 한다.

## 비기능 요구사항

* `NFR-001`: Admin DB 접근 코드와 설정은 대상 업무 DB 연결 또는 MCP 대상 DB 실행 경로로 재사용되어서는 안 된다.
* `NFR-002`: Admin DB가 준비되지 않으면 애플리케이션은 Fail Closed하고 정상 상태인 것처럼 시작해서는 안 된다.
* `NFR-003`: MVP 배포는 단일 FastAPI 인스턴스와 단일 호스트만 지원하며 여러 인스턴스가 하나의 SQLite 파일을 공유해서는 안 된다.
* `NFR-004`: Admin DB 파일은 애플리케이션 이미지 내부의 일시적 경로가 아니라 재시작 후에도 유지할 수 있는 외부 영속 저장 위치를 사용할 수 있어야 한다.
* `NFR-005`: 이 Feature는 Audit Payload에 Secret, 전체 LLM Prompt와 전체 조회 결과를 저장하는 전용 필드를 정의하지 않아야 한다. 실제 Payload Allowlist와 민감정보 마스킹은 후속 Audit Writer에서 강제한다.

## Acceptance Criteria

* [ ] Admin DB와 대상 AdventureWorks2022 DB의 책임과 연결 경로가 분리되어 있다.
* [ ] 지정한 영속 경로에서 SQLite Admin DB를 처음 준비하고 동일한 Schema로 다시 준비할 수 있다.
* [ ] 재초기화 후에도 기존 관리 데이터가 유지되고 Schema 객체가 중복 생성되지 않는다.
* [ ] Slack 사용자 식별자는 중복될 수 없고 활성 상태가 필수이며, 사용자는 하나의 역할만 가지고 허용되지 않은 역할과 역할 누락은 거부된다.
* [ ] 사용자 구조에는 미등록 사용자를 대신하는 기본 사용자나 기본 역할이 없고 활성·비활성 사용자를 구분할 수 있다.
* [ ] 두 MVP 역할에 대해 역할·물리 테이블 단위의 비어 있지 않은 허용 컬럼 집합을 저장하고 구분할 수 있다.
* [ ] 동일한 역할·물리 Schema·Table 조합에 서로 충돌하는 정책을 중복 등록할 수 없다.
* [ ] 정책이 없는 테이블과 허용 컬럼 집합에 없는 컬럼을 암묵적으로 허용하는 데이터 표현이 없다.
* [ ] Wildcard, 빈 컬럼 집합 또는 컬럼 목록 생략으로 전체 컬럼을 허용할 수 없다.
* [ ] 대상 DB에 새 컬럼이 추가되어도 기존 정책에 의해 자동으로 허용되지 않는다.
* [ ] 여러 Audit 이벤트를 Correlation ID로 연결하고 Workflow 단계, Depth, 성공·거부·실패와 재시도를 구분할 수 있다.
* [ ] 실행의 각 단계를 별도 Audit 이벤트로 추가할 수 있으며 후속 이벤트 저장에 기존 실행 요약 행의 수정이 필요하지 않다.
* [ ] 오류 신고는 Correlation ID를 필수로 가지며, 개별 Audit 이벤트를 참조하면 존재하는 이벤트이고 동일한 Correlation ID에 속한다.
* [ ] 필수 관계가 없거나 유효하지 않은 관리 데이터는 저장되지 않는다.
* [ ] Admin DB 경로 접근 또는 Schema 초기화가 실패하면 애플리케이션 시작이 실패한다.
* [ ] Audit Schema에는 Secret, 전체 Prompt와 전체 조회 결과를 위한 전용 필드가 없으며 실제 Payload 제한과 마스킹은 후속 Audit Writer의 책임으로 문서화되어 있다.
* [ ] 설정, Schema 초기화, 관계, 제약과 실패 동작에 대한 자동 테스트가 존재한다.
* [ ] 다중 인스턴스가 하나의 SQLite 파일을 공유하는 구성이 지원 범위에 포함되지 않는다.

## 가정과 제약

* Admin DB 분리는 [ADR 0002](../../adr/0002-admin-db.md)를 따르며, 대상 DB 접근은 [ADR 0007](../../adr/0007-local-stdio-mcp-db-boundary.md)의 MCP 경계를 계속 따른다.
* MVP AWS 데모 배포는 단일 애플리케이션 인스턴스가 로컬 Block Storage로 마운트된 영속 위치의 SQLite 파일을 사용하는 구성을 전제로 한다.
* SQLite는 MVP와 데모의 관리 저장소 선택이며 다중 인스턴스 운영 적합성을 의미하지 않는다.
* `table_policies`는 Business Metadata Catalog가 아니라 역할·물리 테이블 단위의 명시적 허용 컬럼 집합을 저장하는 Governance Metadata다.
* 허용 컬럼 집합을 하나의 컬럼에 저장할지 관계형 구조로 정규화할지는 Spec의 동작을 바꾸지 않는 Plan 단계의 기술 결정이다.
* Business Metadata Retrieval 결과와 Table Policy의 교집합 적용은 후속 ACL·Metadata Feature의 책임이다.
* 미등록 또는 비활성 사용자는 후속 ACL 계층에서 Fail Closed하며 기본 사용자나 역할로 대체하지 않는다.
* 이 Feature는 Admin DB 설정, 연결 Lifecycle, Schema 초기화와 DB 제약 검증까지만 제공한다. 운영용 Repository, 실제 Workflow가 사용자·정책·Audit·오류 신고를 사용하는 동작, Audit Append-Only Writer와 Payload 마스킹은 후속 Feature에서 구현한다.

## 미결정 사항

현재 이 Feature의 Plan 작성에 영향을 주는 요구사항 미결정 사항은 없다. Audit의 장기 보존 기간, 삭제·Archive 정책과 운영 환경의 민감정보 분류 기준은 이 Feature의 범위 밖이며 운영 배포 전에 별도로 결정한다.

## 관련 기준 문서

* 프로젝트 원칙: [README](../../../README.md)
* MVP 범위: [MVP Scope](../../mvp/scope.md)
* MVP 로드맵: [MVP Roadmap](../../mvp/roadmap.md)
* Architecture: [Component Boundaries](../../architecture/component-boundaries.md)
* Architecture: [Project Structure](../../architecture/project-structure.md)
* Architecture: [Query Execution Sequence](../../architecture/query-execution-sequence.md)
* ADR: [0002 Admin Database](../../adr/0002-admin-db.md)
* ADR: [0007 Local stdio MCP DB Boundary](../../adr/0007-local-stdio-mcp-db-boundary.md)
