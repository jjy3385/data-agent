# Schema Inspection Tool 계약 (`inspect_schema` Contract)

> 이 문서는 FastAPI의 MCP Client Manager가 `inspect_schema`를 호출해 AdventureWorks2022의 사용자 정의 Physical Schema 정보를 수집하는 입출력 계약을 정의한다.

## 상태

승인됨 (Accepted). [FEAT-0003 MCP Read-Only Data Access](../features/0003-mcp-readonly-data-access/spec.md)의 구현 기준으로 사용한다.

## 이 문서를 읽는 이유

* Tool에 전달할 수 있는 값을 확인한다.
* Schema Inspection 결과의 구조를 확인한다.
* 실패가 어떻게 구분되는지 확인한다.

이 문서는 MCP Tool의 Wire 입출력 경계만 정의한다. Backend가 이 결과로 Physical Metadata Catalog를 실제로 구성하는 저장 형식, 저장 위치, 캐시와 갱신 방식은 [FEAT-0003 Spec](../features/0003-mcp-readonly-data-access/spec.md)과 Plan을 따르며 이 Contract가 정하지 않는다.

## 범위

이 문서는 `inspect_schema`의 입력, 성공 결과와 오류 전달 규칙을 정의한다. 로컬 `stdio`와 프로세스 Lifecycle을 선택한 이유는 [ADR 0007](../adr/0007-local-stdio-mcp-db-boundary.md)에서 설명한다.

이 Contract의 반환 구조는 Schema·Table·Column·Key·설명을 전달하는 논리적 Physical Metadata 경계를 정의한다. 그러나 FEAT-0003의 MCP Server 구현과 수집 방식은 AdventureWorks2022를 사용하는 MSSQL 전용이다. 시스템 카탈로그 조회, `MS_Description` 수집, 대상 DB Driver와 데이터 타입은 MSSQL에 결합되며, 다른 데이터베이스 제품을 위한 공통 수집 계층이나 Adapter는 MVP 범위에 포함하지 않는다. 향후 다른 관계형 데이터베이스를 지원한다면 해당 제품의 카탈로그와 설명 체계를 사용하는 별도 구현이 이 논리적 반환 구조와 호환되는지를 그 시점에 검토한다.

## 관련 문서

* [MCP 컴포넌트 경계](../architecture/component-boundaries.md)
* [`execute_readonly_query` Contract](execute-readonly-query.md)
* [FEAT-0003 MCP Read-Only Data Access Spec](../features/0003-mcp-readonly-data-access/spec.md)

## 입력 Contract

Tool은 임의 SQL, 자연어 질문, RuntimeIntent, ACL 정보나 LLM Tool Call 원문을 입력으로 받지 않는다. 범용 다중 DB 선택이나 임의 Connection String도 입력으로 받지 않는다. AdventureWorks2022 연결 대상은 MCP Server의 환경설정(`TARGET_DB_*`)으로 결정하며 Tool 입력으로 전달하지 않는다. 기본 동작은 대상 DB의 전체 사용자 정의 Schema Inspection이며, 별도 필터나 범용 옵션을 제공하지 않는다.

| 필드 | 의미 |
|---|---|
| `correlation_id` | 요청, 실행과 Audit을 연결하는 식별자 |

## 성공 반환 Contract

성공한 Tool 호출은 다음 구조의 JSON 직렬화 가능한 결과를 반환한다.
아래 JSON은 Contract 구조를 설명하기 위해 일부 Column만 표시한 축약 예시다. 실제 결과는 검사 대상 Table의 모든 Column과 발견된 Physical FK를 반환하며, FK가 가리키는 Source와 Target Table은 `schemas` 결과에 모두 포함되어야 한다.

```json
{
  "correlation_id": "01JEXAMPLE",
  "schemas": [
    {
      "schema_name": "Production",
      "tables": [
        {
          "table_name": "Product",
          "description": "Products sold or used in the manfacturing of sold products.",
          "columns": [
            {
              "column_name": "ProductID",
              "data_type": "int",
              "is_nullable": false,
              "ordinal_position": 1,
              "description": "Primary key for Product records."
            },
            {
              "column_name": "Name",
              "data_type": "nvarchar",
              "is_nullable": false,
              "ordinal_position": 2,
              "description": "Name of the product."
            }
          ],
          "primary_key": {
            "columns": ["ProductID"]
          }
        },
        {
          "table_name": "ProductInventory",
          "description": "Product inventory information.",
          "columns": [
            {
              "column_name": "ProductID",
              "data_type": "int",
              "is_nullable": false,
              "ordinal_position": 1,
              "description": "Product identification number. Foreign key to Product.ProductID."
            },
            {
              "column_name": "LocationID",
              "data_type": "smallint",
              "is_nullable": false,
              "ordinal_position": 2,
              "description": "Inventory location identification number. Foreign key to Location.LocationID."
            }
          ],
          "primary_key": {
            "columns": ["ProductID", "LocationID"]
          }
        }
      ]
    }
  ],
  "foreign_keys": [
    {
      "foreign_key_name": "FK_ProductInventory_Product",
      "source_schema": "Production",
      "source_table": "ProductInventory",
      "source_columns": ["ProductID"],
      "target_schema": "Production",
      "target_table": "Product",
      "target_columns": ["ProductID"]
    }
  ],
  "summary": {
    "schema_count": 1,
    "table_count": 2
  }
}
```

| 필드 | 의미 |
|---|---|
| `correlation_id` | 요청에서 전달받은 추적 식별자 |
| `schemas` | 검사된 사용자 정의 Schema 목록 |
| `schemas[].schema_name` | Physical Schema 이름 |
| `schemas[].tables` | 해당 Schema의 Table 목록 |
| `schemas[].tables[].table_name` | Physical Table 이름 |
| `schemas[].tables[].description` | Table에 등록된 `MS_Description`. 없으면 `null` |
| `schemas[].tables[].columns` | `ordinal_position` 순서로 정렬된 Column 목록 |
| `schemas[].tables[].columns[].column_name` | Column 이름 |
| `schemas[].tables[].columns[].data_type` | 대상 DB의 Physical 데이터 타입 |
| `schemas[].tables[].columns[].is_nullable` | Nullable 여부 |
| `schemas[].tables[].columns[].ordinal_position` | Table 안에서의 Column 순서(1부터 시작) |
| `schemas[].tables[].columns[].description` | Column에 등록된 `MS_Description`. 없으면 `null` |
| `schemas[].tables[].primary_key` | Primary Key 정보. PK가 없는 Table은 `null` |
| `schemas[].tables[].primary_key.columns` | Key 순서를 보존한 PK Column 이름 목록 |
| `foreign_keys` | 검사 대상 Schema 안에서 발견된 Physical Foreign Key 목록 |
| `foreign_keys[].foreign_key_name` | 대상 DB의 Foreign Key 식별 이름 |
| `foreign_keys[].source_schema` / `source_table` / `source_columns` | FK를 정의한 쪽의 Schema·Table과 Key 순서를 보존한 Column 목록 |
| `foreign_keys[].target_schema` / `target_table` / `target_columns` | FK가 참조하는 쪽의 Schema·Table과 Key 순서를 보존한 Column 목록 |
| `summary.schema_count` | 검사된 Schema 수 |
| `summary.table_count` | 검사된 Table 수 |

시스템 Schema와 시스템 객체는 `schemas`와 `foreign_keys`에 포함하지 않는다. 이 결과는 다음을 포함하지 않는다.

* Business Metadata, Metric·계산식이나 업무 Join 의미
* Virtual FK
* Sample Row
* MCP Server나 LLM이 새로 생성·추론한 자연어 설명
* 대상 DB 자격 증명

## 설명 수집 규칙

* Table과 Column의 `description`은 SQL Server Extended Property 중 `MS_Description`만 읽어 수집한다.
* 등록된 값은 자동 번역·요약·보강하지 않고 문자열 원문으로 반환한다.
* `MS_Description`이 없으면 `null`을 반환하며, 설명이 없다는 이유로 Schema Inspection을 실패시키지 않는다.
* 이 설명은 대상 DB에 등록된 Physical Metadata의 일부다. 업무 용어, Metric, 계산식이나 승인된 업무 의미를 담는 Business Metadata로 간주하거나 자동 승격하지 않는다.

## 직렬화 규칙

* 모든 필드는 JSON 직렬화 가능한 값만 사용한다.
* Column과 PK/FK Column 목록은 항상 원래 순서를 보존한다(복합 Key 포함).

## 오류 규칙

실패는 발생 시점과 책임에 따라 다음과 같이 구분한다. 정확한 Python 예외 클래스 구조는 이 Contract에서 고정하지 않고 Plan 단계에서 결정한다.

### Startup·Readiness 실패

필수 `TARGET_DB_*` 설정이 누락·공백·유효하지 않거나 초기 대상 DB 연결 준비에 실패하면 MCP 실행 경계가 준비된 것으로 처리하지 않고 FastAPI Startup을 완료하지 않는다. 이 실패는 Tool 호출 전에 발생하므로 Tool 오류 응답으로 표현하지 않으며, Secret 실제 값을 오류나 로그에 포함하지 않는다.

### Tool 실행 실패

Schema 조회 권한 부족, Schema Inspection Query Timeout, Schema 조회 실행 실패와 결과 직렬화 실패는 성공 결과와 섞지 않고 MCP Tool 오류로 반환한다. MCP Client Manager는 이를 Backend의 명시적 오류로 변환하며 대상 DB 직접 실행으로 우회하지 않는다.

### Transport·Session 실패

MCP Session 연결 종료, MCP Server 하위 프로세스 종료 또는 `stdio` Transport 단절은 Tool이 정상 오류 응답을 반환하는 경우가 아니다. MCP Client Manager가 연결 종료를 감지해 Backend의 구조화된 연결 오류로 변환하며 대상 DB 직접 실행으로 우회하지 않는다.
