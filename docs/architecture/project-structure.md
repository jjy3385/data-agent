# 프로젝트 모듈 구조 (Project Structure)

> 이 문서는 아키텍처 책임을 FastAPI와 MCP Server의 어느 모듈에 구현할지 보여준다. 실제 파일이 추가되거나 책임이 이동하면 이 문서를 갱신한다.

## 목표 구조

```text
.
├── app/
│   ├── api/                         # API 라우터 (Slack, Admin)
│   ├── core/                        # 설정, 공통 Contract와 정책
│   ├── db/                          # Admin DB 세션
│   ├── mcp/                         # MCP Client Manager와 Lifecycle
│   │   ├── client_manager.py        # SDK Client·Session·직렬화·Call Timeout
│   │   ├── lifecycle.py             # stdio Server 하위 프로세스 시작·종료
│   │   └── contracts.py             # 필수 Tool 입력 Contract 검증
│   ├── models/                      # SQLAlchemy ORM
│   └── services/
│       ├── schema_collector.py      # MCP Tool 결과 → 카탈로그·Physical FK 후보
│       ├── metadata_service.py      # 승인 Metadata, Join, 지표와 정책
│       ├── llm_client.py            # Private LLM 공통 Client
│       ├── intent_resolver.py       # 자연어 → RuntimeIntent
│       ├── metadata_retriever.py    # Intent·ACL 기반 Metadata 검색
│       ├── context_builder.py       # Retrieval 결과 → 제한된 Context
│       ├── query_planner.py         # Metadata Context → QueryPlan
│       ├── plan_validator.py        # MVP Level 1 검증
│       ├── sql_generator.py         # 검증된 QueryPlan → MSSQL
│       ├── sql_guardrail.py         # SQL AST·Allowlist·Plan-SQL 검증
│       ├── xai_generator.py         # 근거 Payload → 사용자 설명
│       └── agent_service.py         # 요청 순서와 Depth·Retry 통제
├── mcp_server/
│   ├── server.py                    # Tool 등록과 stdio 진입점
│   ├── db.py                        # 대상 DB 드라이버·연결 Lifecycle
│   ├── readonly_query_executor.py   # DB Timeout·행 제한·실제 조회
│   └── tools/
│       ├── inspect_schema.py        # 카탈로그·Physical FK 조회 Tool
│       └── execute_readonly_query.py # 검증 완료 SQL 실행 Tool
├── docs/
├── README.md
└── main.py                          # FastAPI 진입점과 Lifespan 등록
```

## 핵심 관계

* `agent_service.py`는 Workflow Orchestrator의 논리적 책임을 구현한다.
* `main.py`는 FastAPI Lifespan을 등록한다.
* Lifespan은 `app/mcp/lifecycle.py`를 통해 MCP Client Manager와 MCP Server 하위 프로세스를 초기화하고 종료한다.
* FastAPI의 `app/db/`는 Admin DB만 다루며 대상 DB 연결을 소유하지 않는다.

## 관련 문서

* [전체 아키텍처](overview.md)
* [컴포넌트 경계](component-boundaries.md)
