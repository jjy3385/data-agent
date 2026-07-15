# 로컬 SQL Server 개발 환경

이 문서는 Docker Desktop에서 SQL Server 2022와 `AdventureWorks2022` 샘플
데이터베이스를 실행하고 관리하는 방법을 설명한다. 프로젝트의 개발 방향과
아키텍처는 루트의 `README.md`를 참고한다.

복원된 71개 테이블의 컬럼·PK·FK·행 수는
[AdventureWorks2022 데이터 구조](../../docs/data/adventureworks2022-schema.md)를
참고한다.

## 1. 현재 구성

`compose.yaml`은 다음 환경을 만든다.

| 항목 | 값 |
|---|---|
| Compose 서비스 | `mssql` |
| 컨테이너 이름 | `data-agent-mssql` |
| 이미지 | `mcr.microsoft.com/mssql/server:2022-latest` |
| 에디션 | Developer Edition |
| Windows 접속 주소 | `127.0.0.1,14330` |
| 컨테이너 SQL Server 포트 | `1433` |
| 데이터 저장소 | Docker named volume `data-agent_mssql-data` |
| 백업 파일 경로 | `docker/mssql/backups/` |
| 컨테이너 백업 경로 | `/var/opt/mssql/backup` |

포트는 Windows에 직접 설치된 SQL Server의 기본 포트 `1433`과 충돌하지
않도록 `14330`을 사용한다. `127.0.0.1`에만 바인딩하므로 다른 PC에서는 이
SQL Server에 직접 접속할 수 없다.

### 자주 쓰는 명령 빠른 참고

모든 명령은 프로젝트 루트에서 실행한다.

| 목적 | 명령 | 데이터 보존 |
|---|---|---|
| 상태 확인 | `docker compose ps` | 예 |
| 실행/필요 시 생성 | `docker compose up -d` | 예 |
| 중지 | `docker compose stop` | 예 |
| 중지된 컨테이너 시작 | `docker compose start` | 예 |
| SQL Server 재시작 | `docker compose restart mssql` | 예 |
| 최근 로그 확인 | `docker compose logs --tail=100 mssql` | 예 |
| 컨테이너와 네트워크 제거 | `docker compose down` | 예 |
| 컨테이너, 네트워크, DB 볼륨 제거 | `docker compose down -v` | **아니요** |

일상적인 개발 종료에는 `docker compose stop`을 사용한다. `down -v`는 복원한
데이터베이스를 포함한 named volume을 삭제하므로 초기화가 목적일 때만 사용한다.

프로젝트 파일 구조는 다음과 같다.

```text
data-agent/
├── .env                              # 로컬 비밀번호, Git 제외
├── compose.yaml
└── docker/
    └── mssql/
        ├── README.md
        └── backups/
            └── AdventureWorks2022.bak # Git 제외
```

## 2. 사전 준비

- Windows에서 Docker Desktop을 실행한다.
- Docker Desktop은 Linux 컨테이너 및 WSL 2 엔진을 사용한다.
- 터미널의 현재 디렉터리를 프로젝트 루트로 이동한다.

```bash
cd /c/workspace/data-agent
docker version
docker compose version
```

`.env`에 SQL Server `sa` 비밀번호를 설정한다.

```dotenv
MSSQL_SA_PASSWORD=<strong-password>
```

비밀번호는 대문자, 소문자, 숫자, 특수문자를 조합한 8자 이상의 값을 사용한다.
`.env`는 Git에서 제외되며 문서, 이슈 또는 채팅에 내용을 붙여넣지 않는다.

Compose 문법과 환경변수 적용 여부는 컨테이너 실행 전에 검사할 수 있다.

```bash
docker compose config --quiet
```

성공하면 아무 내용도 출력하지 않고 종료한다.

## 3. AdventureWorks 백업 준비

Microsoft SQL Server Samples의 AdventureWorks 릴리스에서
`AdventureWorks2022.bak`를 내려받아 다음 위치에 둔다.

```text
docker/mssql/backups/AdventureWorks2022.bak
```

공식 다운로드 주소:

```text
https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks2022.bak
```

Git Bash에서 내려받는 예시는 다음과 같다.

```bash
mkdir -p docker/mssql/backups
curl -fL \
  -o docker/mssql/backups/AdventureWorks2022.bak \
  https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks2022.bak
```

백업 파일과 SQL Server 데이터 파일(`.mdf`, `.ndf`, `.ldf`)은 Git에서
제외된다.

## 4. 컨테이너 최초 실행

이미지를 내려받고 컨테이너, 네트워크, named volume을 생성한 뒤 SQL Server를
백그라운드에서 실행한다.

```bash
docker compose up -d
```

상태를 확인한다.

```bash
docker compose ps
```

정상 상태는 `Up`이며 포트는 다음처럼 표시된다.

```text
127.0.0.1:14330->1433/tcp
```

SQL Server 준비 상태는 로그로 확인한다.

```bash
docker compose logs --tail=100 mssql
```

다음 문구가 있으면 접속할 수 있다.

```text
SQL Server is now ready for client connections.
```

실시간 로그를 보려면 다음 명령을 사용하고 `Ctrl+C`로 로그 보기만 종료한다.

```bash
docker compose logs -f mssql
```

## 5. AdventureWorks2022 최초 복원

이 절은 named volume에 `AdventureWorks2022`가 아직 없을 때 한 번만 실행한다.

### 5.1 백업 파일 연결 확인

Git Bash는 `/var/...` 경로를 Windows 경로로 자동 변환할 수 있다. 컨테이너
내부의 Linux 절대경로를 인자로 전달할 때는 현재 명령에
`MSYS_NO_PATHCONV=1`을 지정한다.

```bash
MSYS_NO_PATHCONV=1 docker compose exec mssql \
  ls -lh /var/opt/mssql/backup/AdventureWorks2022.bak
```

### 5.2 SQL Server 접속 확인

```bash
MSYS_NO_PATHCONV=1 docker compose exec mssql bash -lc \
  '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "SELECT @@VERSION AS version;"'
```

`-C`는 로컬 컨테이너가 생성한 자체 서명 인증서를 신뢰하도록 한다.

### 5.3 백업 논리 파일명 확인

```bash
MSYS_NO_PATHCONV=1 docker compose exec mssql bash -lc \
  "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -s '|' -W -Q \"RESTORE FILELISTONLY FROM DISK = N'/var/opt/mssql/backup/AdventureWorks2022.bak';\""
```

현재 공식 백업에서 사용하는 논리 파일명은 다음과 같다.

```text
AdventureWorks2022
AdventureWorks2022_log
```

다른 백업을 사용할 때는 `RESTORE FILELISTONLY` 결과에 맞게 이후 명령의
논리 파일명을 변경한다.

### 5.4 복원 가능 여부 검사

이 명령은 데이터베이스를 생성하지 않고 백업과 대상 경로를 검사한다.

```bash
MSYS_NO_PATHCONV=1 docker compose exec mssql bash -lc \
  "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -Q \"RESTORE VERIFYONLY FROM DISK = N'/var/opt/mssql/backup/AdventureWorks2022.bak' WITH MOVE N'AdventureWorks2022' TO N'/var/opt/mssql/data/AdventureWorks2022.mdf', MOVE N'AdventureWorks2022_log' TO N'/var/opt/mssql/data/AdventureWorks2022_log.ldf';\""
```

정상 결과:

```text
The backup set on file 1 is valid.
```

### 5.5 데이터베이스 복원

다음 명령은 named volume에 실제 `.mdf`, `.ldf` 파일을 생성한다. 기존
데이터베이스를 실수로 덮어쓰지 않도록 `REPLACE`는 사용하지 않는다.

```bash
MSYS_NO_PATHCONV=1 docker compose exec mssql bash -lc \
  "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -Q \"RESTORE DATABASE [AdventureWorks2022] FROM DISK = N'/var/opt/mssql/backup/AdventureWorks2022.bak' WITH MOVE N'AdventureWorks2022' TO N'/var/opt/mssql/data/AdventureWorks2022.mdf', MOVE N'AdventureWorks2022_log' TO N'/var/opt/mssql/data/AdventureWorks2022_log.ldf', RECOVERY, STATS = 10;\""
```

마지막에 `RESTORE DATABASE successfully processed`가 출력되면 성공이다.

### 5.6 복원 상태 확인

```bash
MSYS_NO_PATHCONV=1 docker compose exec mssql bash -lc \
  "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -W -s '|' -Q \"SELECT name, state_desc, recovery_model_desc, compatibility_level, user_access_desc FROM sys.databases WHERE name = N'AdventureWorks2022';\""
```

정상 상태:

```text
AdventureWorks2022|ONLINE|SIMPLE|160|MULTI_USER
```

## 6. 일상적인 실행과 종료

### 상태 확인

```bash
docker compose ps
```

### 중지한 기존 컨테이너 시작

```bash
docker compose start
```

### 컨테이너 중지

```bash
docker compose stop
```

`stop`은 컨테이너를 삭제하지 않는다. 다음 `start`가 빠르고 데이터도 그대로
유지된다. 평소 개발을 마칠 때 권장하는 명령이다.

### SQL Server 재시작

```bash
docker compose restart mssql
```

### 컨테이너가 없으면 생성하고 실행

```bash
docker compose up -d
```

이미 컨테이너가 있으면 필요한 변경사항만 반영하고 실행 상태로 만든다.

### 컨테이너와 Compose 네트워크 제거

```bash
docker compose down
```

`down`은 컨테이너와 Compose 네트워크를 제거하지만 named volume과
`AdventureWorks2022` 데이터는 보존한다. 나중에 `docker compose up -d`를
실행하면 보존된 데이터로 컨테이너가 다시 만들어진다.

### 주의: 데이터까지 완전히 삭제

```bash
docker compose down -v
```

> `-v`는 `data-agent_mssql-data` named volume을 삭제한다. 복원한
> `AdventureWorks2022`와 SQL Server 내부 데이터가 모두 사라지므로 환경을
> 처음부터 초기화하려는 경우에만 사용한다. 호스트의 `.bak` 파일은 삭제되지
> 않는다.

## 7. 이미지 업데이트

SQL Server 2022 최신 이미지를 내려받고 컨테이너를 다시 만든다.

```bash
docker compose pull mssql
docker compose up -d
```

데이터는 named volume에서 다시 연결된다. 업데이트 전에는 중요한 개발
데이터를 별도로 백업하는 것이 안전하다. 완전한 재현성이 필요해지면
`2022-latest` 대신 검증한 특정 이미지 버전 또는 digest로 고정한다.

## 8. SSMS 연결

Windows의 SQL Server Management Studio에서 다음 값을 사용한다.

| 항목 | 값 |
|---|---|
| Server type | `Database Engine` |
| Server name | `127.0.0.1,14330` |
| Authentication | `SQL Server Authentication` |
| Login | `sa` |
| Password | `.env`의 `MSSQL_SA_PASSWORD` 값 |
| Encryption | `Mandatory` |
| Trust server certificate | 체크 |

SQL Server 포트는 콜론이 아니라 쉼표로 구분한다. 즉
`127.0.0.1:14330`이 아니라 `127.0.0.1,14330`을 사용한다.

연결 후 Object Explorer에서 다음 위치를 확인한다.

```text
Databases
└── AdventureWorks2022
    └── Tables
```

연결 확인 쿼리:

```sql
USE AdventureWorks2022;

SELECT
    DB_NAME() AS current_database,
    @@SERVERNAME AS server_name,
    @@VERSION AS sql_server_version;
```

## 9. 데이터 빠르게 살펴보기

스키마별 테이블 수:

```sql
SELECT
    s.name AS schema_name,
    COUNT(*) AS table_count
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON s.schema_id = t.schema_id
GROUP BY s.name
ORDER BY s.name;
```

제품 예시:

```sql
SELECT TOP (20)
    ProductID,
    Name,
    ProductNumber,
    Color,
    ListPrice
FROM Production.Product
ORDER BY ProductID;
```

최근 주문 예시:

```sql
SELECT TOP (20)
    SalesOrderID,
    OrderDate,
    CustomerID,
    SubTotal,
    TaxAmt,
    Freight,
    TotalDue
FROM Sales.SalesOrderHeader
ORDER BY OrderDate DESC;
```

주요 업무 스키마:

- `HumanResources`: 직원, 부서, 근무 이력
- `Person`: 사람, 주소, 연락처
- `Production`: 제품, 재고, 부품 구성, 작업지시
- `Purchasing`: 공급업체, 구매 주문
- `Sales`: 고객, 영업 담당자, 판매 주문

## 10. 문제 해결

### 컨테이너가 실행되지 않는 경우

```bash
docker compose ps -a
docker compose logs --tail=200 mssql
```

비밀번호 정책, 포트 충돌, Docker Desktop 메모리 부족 여부를 확인한다.

### Git Bash가 컨테이너 경로를 변환하는 경우

다음과 같은 잘못된 경로가 오류에 표시될 수 있다.

```text
C:/Program Files/Git/var/opt/mssql/...
```

해당 Docker 명령 앞에 `MSYS_NO_PATHCONV=1`을 붙인다.

### SSMS 인증서 오류

SSMS에서 다음 옵션을 사용한다.

```text
Encryption: Mandatory
Trust server certificate: 체크
```

### SSMS 로그인 오류 18456

- 인증 방식을 `SQL Server Authentication`으로 선택했는지 확인한다.
- 로그인 이름이 `sa`인지 확인한다.
- `.env`의 비밀번호를 정확하게 입력한다.

### 포트 접속 오류

```bash
docker compose ps
```

상태가 `Up`이고 다음 포트 매핑이 표시되는지 확인한다.

```text
127.0.0.1:14330->1433/tcp
```

## 11. 애플리케이션 Read-Only 계정

Python 애플리케이션은 SQL Server 관리 계정인 `sa`를 사용하지 않고
`data_agent_ro`를 사용한다.

`data_agent_ro`의 `AdventureWorks2022` 권한은 다음과 같다.

- `db_datareader`: 모든 사용자 테이블과 View를 조회할 수 있다.
- `db_denydatawriter`: 사용자 테이블의 `INSERT`, `UPDATE`, `DELETE`를 거부한다.
- 데이터베이스 수준 `EXECUTE` 권한을 거부한다.
- DDL 및 서버 관리 권한을 부여하지 않는다.

애플리케이션은 다음 환경변수로 접속 정보를 읽는다.

| 환경변수 | 로컬 개발 값 또는 용도 |
|---|---|
| `TARGET_DB_HOST` | `127.0.0.1` |
| `TARGET_DB_PORT` | `14330` |
| `TARGET_DB_NAME` | `AdventureWorks2022` |
| `TARGET_DB_USER` | `data_agent_ro` |
| `TARGET_DB_PASSWORD` | Read-Only 계정 비밀번호 |
| `TARGET_DB_DRIVER` | `ODBC Driver 18 for SQL Server` |
| `TARGET_DB_ENCRYPT` | 로컬에서도 암호화 연결을 사용하므로 `yes` |
| `TARGET_DB_TRUST_SERVER_CERTIFICATE` | 로컬 자체 서명 인증서이므로 `yes` |

실제 비밀번호는 Git에서 제외되는 루트 `.env`에만 저장한다. 현재 로컬
튜토리얼 환경에서는 `TARGET_DB_PASSWORD`가 `MSSQL_SA_PASSWORD`를 참조하지만,
운영 환경에서는 반드시 별도 비밀번호와 비밀 저장소를 사용한다.
`.env.example`에는 실제 비밀번호를 기록하지 않는다.

## 12. 보안 원칙

- `sa`는 로컬 초기 구성과 관리에만 사용한다.
- 애플리케이션은 이후 별도의 최소 권한 read-only 로그인을 사용한다.
- `.env`와 백업 파일을 Git에 커밋하지 않는다.
- 호스트 포트는 `127.0.0.1`에만 바인딩한다.
- 백업 디렉터리는 컨테이너에 `:ro`로 마운트한다.
- 운영 환경에서는 Developer Edition과 자체 서명 인증서를 사용하지 않는다.
