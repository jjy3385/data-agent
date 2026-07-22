# 0008. 단일 EC2·EBS 기반 AWS 데모 배포

## 상태 (Status)

제안됨 (Proposed)

## 배경 (Context)

3주 MVP는 로컬에서 완성한 Jinja2 데모 웹 UI와 Depth 1 Workflow를 AWS에 일찍 배포해 실제 시연 가능한 상태로 만들어야 한다. 현재 목표는 고가용성 운영 환경이 아니라 설치, 장애 확인과 재배포가 단순한 단일 사용자 중심의 데모 환경이다.

Admin DB는 [ADR 0002](0002-admin-db.md)에 따라 SQLite를 사용하고, 대상 AdventureWorks2022 접근은 [ADR 0007](0007-local-stdio-mcp-db-boundary.md)에 따라 FastAPI가 관리하는 로컬 `stdio` MCP Server를 통해서만 수행한다.

## 결정 (Decision)

AWS 데모는 단일 EC2와 EBS를 사용한다.

1. FastAPI는 워커 하나로 실행하고 로컬 `stdio` MCP Server 하위 프로세스 하나를 관리한다.
2. AdventureWorks2022 SQL Server는 같은 데모 호스트에서 실행하며 외부에 DB Port를 공개하지 않는다.
3. SQLite Admin DB와 데모에 필요한 영속 데이터는 EBS에 저장한다.
4. 외부에는 데모 웹 UI와 필요한 HTTP Endpoint만 제한적으로 공개한다.
5. 대상 DB 자격 증명과 LLM Secret은 이미지나 저장소에 포함하지 않고 배포 환경 설정으로 주입한다.
6. 재시작과 재배포 후 Admin DB 데이터가 유지되는지 검증한다.
7. RDS, 다중 인스턴스, 고가용성, 자동 확장, CI/CD와 IaC는 Post-MVP 범위로 둔다.

## 결과 (Consequences)

* 로컬과 AWS 데모가 같은 FastAPI·로컬 MCP 실행 경계를 사용한다.
* 별도 RDS나 원격 MCP Service 없이 배포 구성을 단순하게 유지할 수 있다.
* 애플리케이션과 대상 DB가 한 호스트의 CPU, Memory, Storage와 장애 영역을 공유한다.
* EC2 또는 EBS 장애에 대한 고가용성과 자동 복구를 제공하지 않는다.
* 운영 환경으로 확장할 때 Admin DB, 대상 DB와 MCP 배포 경계를 다시 검토해야 한다.

## 관련 문서

* [MVP 로드맵](../mvp/roadmap.md)
* [MVP 범위](../mvp/scope.md)
* [ADR 0002 Admin DB](0002-admin-db.md)
* [ADR 0007 로컬 stdio MCP 경계](0007-local-stdio-mcp-db-boundary.md)
