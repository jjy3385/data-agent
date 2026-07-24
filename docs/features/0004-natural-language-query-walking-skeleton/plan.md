# 자연어 질문 처리 최소 동작 흐름 (Walking Skeleton) Plan

* Feature ID: `FEAT-0004`
* Status: `Approved`(Token 상한 확정값을 실제 구현값과 동기화한 뒤 사용자가 재승인함. 검토 기록의 마지막 행 참고)
* Development Track: `Standard`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)

## 구현 목표

Approved Spec의 대표 재고 질문 하나가 HTTP 자연어 요청 → RuntimeIntent → Metadata Context → QueryPlan → MSSQL → FEAT-0003 MCP 실행 → Bounded Result 응답까지 실제로 연결되는 Depth 1 Walking Skeleton을 구현한다. FR-001~FR-010, NFR-001~NFR-005를 충족하고, LLM 산출물은 각 단계에서 Backend가 검증한 뒤에만 다음 단계로 진행하며, SQL은 MCP 호출 전 Backend 자체 최소 검증을 통과해야 한다.

## 관련 기준과 준수 여부

* README 원칙: LLM은 승인된 Metadata만 사용하고 SQL 실행 권한을 갖지 않는다(원칙 2, 3). FastAPI는 대상 DB에 직접 연결하지 않는다(원칙 4). 이 Plan은 모든 대상 DB 접근을 FEAT-0003 `MCPClientManager`로만 수행한다.
* ADR: [0001](../../adr/0001-readonly-db.md)·[0007](../../adr/0007-local-stdio-mcp-db-boundary.md)(Accepted, MCP 경계 그대로 재사용) — 새 SQL 실행 경로를 만들지 않는다. [0004](../../adr/0004-agent-depth.md)(Proposed) — Depth 1만 실행하므로 이 Plan은 그 결정에 의존하지 않는다.
* Architecture: [컴포넌트 책임과 경계](../../architecture/component-boundaries.md)의 Workflow Orchestrator/LLM Provider 책임, [질문 처리 시퀀스](../../architecture/query-execution-sequence.md) 1~12단계(Week 1 범위), [프로젝트 모듈 구조](../../architecture/project-structure.md)가 이미 지정한 `app/services/*` 파일 배치를 그대로 따른다.
* Contract: [RuntimeIntent](../../contracts/runtime-intent.md), [QueryPlan](../../contracts/query-plan.md), [자연어 질문 API](../../contracts/natural-language-query.md), [`execute_readonly_query`](../../contracts/execute-readonly-query.md)(Accepted) — 모두 그대로 구현 기준으로 사용하며 필드·Enum·불변조건을 변경하지 않는다.

충돌하거나 변경이 필요한 기준 문서는 없다.

## 기술적 접근

**FastAPI Settings의 `.env` 로딩과 LLM 설정 인식**: 기존 `app/core/config.py`의 `Settings`가 `SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")`로 저장소 루트 `.env`를 읽도록 확장한다(`mcp_server/db.py`의 `TargetDBSettings`와 동일한 패턴). 실제 OS 환경변수가 `.env`보다 우선하며(pydantic-settings 기본 우선순위) `os.environ` 자체는 변경하지 않는다. 기존 `app_env`/`admin_db_path`와 신규 `llm_provider`/`llm_model`/`llm_api_key`/`llm_base_url`을 같은 `Settings`에서 관리한다(공유 `env_prefix` 없이 필드명이 그대로 대문자 환경변수 이름과 일치). `mcp_server/db.py`의 `TARGET_DB_*` 소유권과 `.env` 로딩 방식은 바꾸지 않는다 — FastAPI `Settings`와 MCP Server `TargetDBSettings`는 계속 분리된 두 `BaseSettings` Instance다. 테스트에서 실제 `.env`·Secret을 격리해야 하면 `Settings(_env_file=None, ...)`로 직접 구성하거나 `monkeypatch.setenv(...)`로 OS 환경변수를 덮어써 우선순위로 격리한다(OS 환경변수가 `.env`보다 항상 우선하므로 기존 `admin_db_path` Fixture의 `monkeypatch.setenv` 패턴은 그대로 유지된다).

**LLM SDK, 비동기 호출과 단일 Provider 규칙**: `openai` Python SDK(`openai>=2.8,<3`, `AsyncOpenAI`)만 추가한다. `chat.completions.create` 인터페이스는 동기 `OpenAI`와 비동기 `AsyncOpenAI` 사이에서 동일하므로 비동기 전환이 요청·응답 처리 로직 자체를 바꾸지 않는다. FastAPI Event Loop를 네트워크 호출로 막지 않기 위해 `llm_client.py`의 모든 메서드는 `async def`다. `LLM_PROVIDER`를 받기만 하고 무시하지 않도록 다음 규칙을 확정한다: `LLM_BASE_URL`이 없으면 공식 OpenAI Endpoint를 사용하며 이때 `LLM_PROVIDER`는 trim 후 정확히 `"openai"`여야 한다. `LLM_BASE_URL`이 있으면 `LLM_PROVIDER`는 비어 있지 않은 임의의 식별 문자열이면 되고 SDK 선택을 분기하지 않는다(Client는 두 경우 모두 동일한 `AsyncOpenAI`). 두 경우 모두 `LLM_MODEL`·`LLM_API_KEY`는 공백 없이 필수다. 실제 Provider·모델은 JSON Mode(`response_format={"type": "json_object"}`)와 `max_completion_tokens` Parameter를 지원하는 OpenAI 호환 조합이어야 한다(실행 환경 조건). 이 규칙을 만족하지 않으면 `LLMUnavailableError`를 던진다. 실제 Provider·모델·API Key·Base URL 값은 이 Plan이 고정하지 않으며 구현 실행 전 `.env`로 준비하고, 실제 검증에 사용한 Provider·모델명만 `tasks.md`에 기록하고 API Key는 어떤 문서·로그·Skip Reason에도 남기지 않는다.

**LLM Client Wrapper와 내부 Instance의 Lifecycle 분리**: `app/core/lifespan.py`는 설정 검증이나 네트워크 호출을 하지 않는 `OpenAICompatibleLLMClient()` Wrapper 객체만 생성해 `app.state.llm_client`에 저장한다(생성 자체는 항상 성공하며 Startup을 절대 막지 않는다). 이 Wrapper는 내부 `AsyncOpenAI` Instance를 갖지 않은 상태로 시작하며, 첫 `complete_json()`/`complete_text()` 호출에서 `get_settings()`로 Provider 규칙을 검증한 뒤 `AsyncOpenAI(api_key=..., base_url=..., timeout=20.0, max_retries=1)`를 지연 생성해 이후 호출까지 재사용한다. 설정이 유효하지 않으면 내부 Instance를 만들지 않고 매 요청마다 `LLMUnavailableError`를 반환한다(캐시된 실패 상태를 두지 않고 매번 `get_settings()`를 다시 읽으므로 `.env`가 나중에 고쳐져도 재시도된다). 이미 내부 Instance가 있는 상태에서 일시적인 API 호출 실패(Rate Limit, Timeout, Connection Error)가 나도 그 Instance를 폐기하지 않고 다음 요청에서 그대로 재사용한다 — 실패는 호출 단위 예외로만 처리한다. `aclose()`는 내부 Instance가 없으면 아무 것도 하지 않고(no-op), 있으면 `app/core/lifespan.py`의 종료 경로에서 정확히 한 번 호출해 정리한다. Timeout `20.0`은 SDK 내부 Retry(`max_retries=1`)를 포함한 호출 전체의 상한이 아니라 SDK가 개별 시도에 적용하는 값이므로, `complete_json`/`complete_text`는 SDK 호출을 `asyncio.timeout(20)`으로 한 번 더 감싸 Retry를 포함한 전체 호출이 20초를 넘으면 `asyncio.TimeoutError`를 `LLMUnavailableError`로 변환한다. 출력 Token 상한은 호출부가 `max_completion_tokens`로 지정한다: RuntimeIntent 2000, QueryPlan 3000, SQL 2000(최초 확정값은 각각 500/800/600이었으나, 구현 단계에서 실제 설정된 LLM Provider로 호출한 결과 응답이 완성되기 전에 `max_completion_tokens` 예산을 모두 소비해 `finish_reason: "length"`로 JSON·SQL이 중간에 잘리는 현상을 확인했다 — 숨겨진 reasoning Token이 가시 출력보다 먼저 예산을 소비하기 때문이다. 확대한 값에서는 완전한 응답을 받는 것을 확인했다. 호출당 Token 예산이 늘어난 만큼 요청당 비용과 응답 지연이 증가할 수 있다). 내부 `AsyncOpenAI` Instance가 한 번 생성된 이후 `.env`의 Provider·모델·API Key·Base URL을 바꿔도 이미 생성된 Instance에는 자동 반영되지 않으며, 반영하려면 애플리케이션을 재시작해야 한다(Hot Reload는 구현하지 않는다).

**구조화 출력 방식과 기각한 대안**: RuntimeIntent와 QueryPlan은 `chat.completions.create(response_format={"type": "json_object"}, ...)`(기본 JSON Mode)로 받아 문자열을 `json.loads()`한 뒤 각 Contract에 대응하는 Pydantic Model로 검증한다. OpenAI Structured Outputs의 `strict` JSON Schema는 검토했지만 채택하지 않았다: `strict` 모드는 모든 Property를 스키마에 고정해야 해 `explicit_parameters`·`filters[].parameters`처럼 LLM이 임의 Key를 선택하는 개방형 Object를 표현할 수 없다. `FR-009`가 LLM 산출물을 항상 Backend가 재검증하도록 요구하므로 기본 JSON Mode와 Pydantic 검증만으로 충분하다. SQL 생성은 JSON이 아니므로 `response_format` 없이 텍스트 완성을 사용하고 응답에서 SQL 문자열만 추출한다.

**Business Metadata 저장과 Physical Metadata Catalog 결합**: Week 1 Business Metadata는 관리 UI나 Admin DB Schema 없이 `app/services/metadata_service.py`의 정적 Python 레지스트리로 관리한다. 대표 질문 하나에 필요한 Entity(`product`) 1개, Dimension(`product_id`, `product_name`) 2개, Metric(`current_inventory`, `safety_stock_level`) 2개, Filter(`below_safety_stock`) 1개, Grain(`product`) 1개, Join(`product_to_product_inventory`) 1개만 등록하며, 각 항목은 물리 매핑(Schema·Table·Column, 집계 방식)과 아래 Alias 규칙에서 쓰는 승인 Alias 목록을 함께 갖는다. `app/core/lifespan.py`가 FEAT-0003의 `PhysicalMetadataCatalog` 구성 직후 `metadata_service.validate_physical_mapping(catalog)`를 호출해 가정한 Table·Column·FK가 실제 Catalog에 있는지 대조하고, 불일치하면 `BusinessMetadataMappingError`가 그대로 전파되어 기존 MCP Startup 실패와 동일하게 ASGI Startup을 완료시키지 않는다. Week 1의 고정 Demo Scope는 이 레지스트리 전체와 같다.

**Metadata 검색 Alias 규칙**(RuntimeIntent → Business Metadata 검색, SQL Table Alias와는 별개): `metadata_retriever.retrieve()`는 `intent.subject`와 `intent.requested_concepts`의 각 문자열을 trim 후 소문자로 정규화하고, 승인된 Alias 집합과 정확히 일치하는지만 비교한다. Entity Alias(`product` 매칭 대상): `{"product", "제품", "품목", "상품"}`. Concept Alias는 `inventory`: `{"inventory", "stock", "재고", "현재 재고", "재고량"}`, `safety_stock`: `{"safety_stock", "safety stock", "안전재고", "안전 재고", "최소 재고"}`. `subject`가 Entity Alias와 일치하고 `requested_concepts`가 `inventory`·`safety_stock` 두 그룹에 각각 최소 1개 일치해야 검색이 성공하며, 그렇지 않으면 `MetadataNotFoundError`. 질문 원문 전체나 SQL을 직접 대상으로 하지 않는다(NFR-003).

**Backend SQL 최소 검증 방식**: 정규식·토큰 기반 검사를 선택하고 SQL Parser 라이브러리는 도입하지 않는다. Parser 기반 검증은 Table·Column·Alias·Subquery를 구조적으로 해석할 수 있어 더 견고하지만 FEAT-0006의 SQL AST Guardrail·Plan-SQL Match 범위이므로 지금 당겨오면 NFR-003의 Week 1/FEAT-0006 경계가 흐려진다. `mcp_server/readonly_query_executor.py`가 이미 같은 방식(단어 경계 정규식)으로 최소 안전성을 검증한 전례가 있으므로 Backend도 같은 수준의 방식을 사용하되 검증 항목은 더 넓다(허용 Table·Column·Alias Allowlist, Wildcard 금지, TOP 상한, 결정적 정렬까지 포함). Week 1 대표 질문은 문자열 Literal이 필요 없으므로 문자열을 파싱·마스킹하지 않고 통째로 거부해(Fail Closed) 규칙을 단순하게 유지한다. 정확한 12개 규칙은 "오류·보안·경계 처리" 절에 구현자가 그대로 따를 수 있는 순서로 명시한다. Backend와 MCP Server는 SELECT-only·단일 Statement·금지 키워드를 각자 독립적인 신뢰 경계에서 의도적으로 중복 검증하며, 어느 한쪽도 다른 쪽의 대체물이 아니다.

**불필요한 추상화를 피하는 방법**: Provider 추상 클래스, Plugin Registry, 범용 Metadata Import 파이프라인을 만들지 않는다. `LLMClient`는 테스트 대체를 위한 최소 `Protocol` 하나이며 구현체는 `OpenAICompatibleLLMClient` 하나뿐이다. `metadata_service.py`는 정적 데이터 조회 함수만 제공한다. `validation_exception_handler`는 새 Middleware나 Router 구조를 만들지 않고 기존 FastAPI `RequestValidationError` Handler 등록 지점 하나만 사용해 경로별로 분기한다.

## 모듈과 파일 책임

| 파일 | 책임 | 변경 |
|---|---|---|
| `app/core/config.py` | `SettingsConfigDict(env_file=REPO_ROOT/".env")`로 `.env` 로딩 추가, `llm_provider`/`llm_model`/`llm_api_key`/`llm_base_url`(선택) 추가 | 수정 |
| `app/core/lifespan.py` | Catalog 구성 뒤 `validate_physical_mapping()` 호출, `OpenAICompatibleLLMClient()` 생성(검증 없이)·`app.state.llm_client` 저장, 종료 시 `aclose()` | 수정 |
| `app/services/metadata_service.py` | 고정 Demo Scope Business Metadata 정적 레지스트리(승인 Alias 포함), Catalog 대조 검증 | 추가 |
| `app/services/llm_client.py` | `LLMClient` Protocol, 비동기 단일 Provider Client, 지연 생성 Lifecycle, `is_configured()`, `LLMUnavailableError` | 추가 |
| `app/services/intent_resolver.py` | 주입된 `LLMClient`로 RuntimeIntent 비동기 생성, RuntimeIntent Contract Pydantic 검증 | 추가 |
| `app/services/metadata_retriever.py` | RuntimeIntent 기반 Alias 매칭, Demo Scope 판정, `MetadataNotFoundError` | 추가 |
| `app/services/context_builder.py` | 검색된 Business Metadata를 LLM에 전달할 제한된 Metadata Context로 변환 | 추가 |
| `app/services/query_planner.py` | 주입된 `LLMClient`로 QueryPlan 비동기 생성, QueryPlan Contract 구조 Pydantic Model | 추가 |
| `app/services/plan_validator.py` | QueryPlan Backend 의미 검증(Level 1: ID 존재, Demo Scope, `depth`, `grain_id`, `order_by`, `limit`) | 추가 |
| `app/services/sql_generator.py` | 주입된 `LLMClient`로 검증된 QueryPlan·Metadata Context → MSSQL 비동기 생성(`AS` Table Alias·승인 출력 Alias 사용을 Prompt로 지시) | 추가 |
| `app/services/sql_guardrail.py` | MCP 호출 전 Backend 최소 SQL 검증(12개 규칙), `SqlRejectedError` | 추가 |
| `app/services/agent_service.py` | Correlation ID 사용, 단계별 호출 순서, 예외 → 공개 `code` Enum을 갖는 Discriminated `QuestionOutcome` 매핑 | 추가 |
| `app/api/query.py` | Contract 불변조건을 강제하는 요청/응답 Model, `/api/questions` 전용 `RequestValidationError` Handler(다른 경로는 FastAPI 기본 Handler로 위임), Router, Dependency 함수 | 추가 |
| `main.py` | `query.router`와 `validation_exception_handler` 등록 | 수정 |
| `pyproject.toml` | `openai>=2.8,<3` 의존성, `requires_llm` pytest marker | 수정 |
| `tests/conftest.py` | `FAKE_INSPECT_SCHEMA_RESULT`에 `Production.Product.SafetyStockLevel`과 `Production.ProductInventory`(`ProductID`, `Quantity`) Table·PK·둘 사이 Physical FK 추가(FEAT-0004 최소 물리 매핑과 일치), `LLMClient` Protocol을 구현하는 `FakeLLMClient`, `RUN_LLM_TESTS`와 `llm_client.is_configured()`를 함께 확인하는 `requires_llm` 자동 Skip Hook | 수정 |
| `tests/` (신규) | 8절 범주에 대응하는 자동 테스트 | 추가 |

`app/db/`, `app/models/`, `mcp_server/`, FEAT-0003 파일은 변경하지 않는다.

## 공개 경계

```python
# app/services/llm_client.py
class LLMUnavailableError(RuntimeError): ...

class LLMClient(Protocol):
    async def complete_json(self, system_prompt: str, user_prompt: str, max_completion_tokens: int) -> dict[str, Any]: ...
    async def complete_text(self, system_prompt: str, user_prompt: str, max_completion_tokens: int) -> str: ...

class OpenAICompatibleLLMClient:
    """Wrapper 생성 자체는 검증·네트워크 호출을 하지 않는다. 첫 호출에서 get_settings()로
    Provider 규칙을 검증하고 AsyncOpenAI를 지연 생성해 재사용한다. asyncio.timeout(20)으로
    SDK Retry를 포함한 호출 전체를 제한한다. 설정 실패는 내부 Instance를 만들지 않고 매
    요청마다 재시도된다. 일시적 호출 실패는 이미 만든 Instance를 폐기하지 않는다."""

    def __init__(self) -> None: ...
    async def complete_json(self, system_prompt: str, user_prompt: str, max_completion_tokens: int) -> dict[str, Any]: ...
    async def complete_text(self, system_prompt: str, user_prompt: str, max_completion_tokens: int) -> str: ...
    async def aclose(self) -> None:
        """내부 AsyncOpenAI Instance가 없으면 no-op, 있으면 정확히 한 번 정리한다."""

def is_configured() -> bool:
    """OpenAICompatibleLLMClient와 동일한 get_settings() 기반 Provider 규칙 검증 결과만
    반환한다(API Key 값 자체는 반환·로그하지 않음). requires_llm 자동 Skip 판단에 사용."""


# app/services/intent_resolver.py
class IntentContractViolationError(RuntimeError): ...

class RuntimeIntent(BaseModel): ...  # runtime-intent.md 7개 필드 그대로

async def generate_runtime_intent(question: str, llm_client: LLMClient) -> RuntimeIntent:
    """LLM 호출 후 RuntimeIntent Contract(Enum, 필수 조건, 추가 필드 금지)를 검증해 반환.
    위반 시 IntentContractViolationError. requires_clarification=true는 유효한 반환값이다."""


# app/services/metadata_retriever.py
class MetadataNotFoundError(RuntimeError): ...

def retrieve(intent: RuntimeIntent) -> list[MetadataEntry]:
    """기술적 접근의 Alias 규칙으로 subject/requested_concepts를 매칭한다.
    product+inventory+safety_stock 조합이 모두 확보되지 않으면 MetadataNotFoundError."""


# app/services/context_builder.py
class MetadataContext(BaseModel):
    entities: dict[str, MetadataEntry]
    dimensions: dict[str, MetadataEntry]
    metrics: dict[str, MetadataEntry]
    filters: dict[str, MetadataEntry]
    grains: dict[str, MetadataEntry]
    joins: dict[str, MetadataEntry]

    def known_ids(self) -> set[str]: ...

def build(entries: list[MetadataEntry]) -> MetadataContext: ...


# app/services/query_planner.py
class QueryPlan(BaseModel): ...  # query-plan.md 구조 그대로(구조적 검증만)

async def generate_query_plan(intent: RuntimeIntent, context: MetadataContext, llm_client: LLMClient) -> QueryPlan: ...


# app/services/plan_validator.py
class QueryPlanInvalidError(RuntimeError): ...

def validate(plan: QueryPlan, context: MetadataContext) -> QueryPlan:
    """ID 존재, depth=1, grain_id="product", order_by[0]=(product_id, asc),
    limit<=MAXIMUM_RETURNED_ROWS를 확인. 위반 시 QueryPlanInvalidError."""


# app/services/sql_generator.py
async def generate_sql(plan: QueryPlan, context: MetadataContext, llm_client: LLMClient) -> str: ...


# app/services/sql_guardrail.py
class SqlRejectedError(RuntimeError): ...

def validate(sql: str, context: MetadataContext) -> str:
    """오류·보안·경계 처리 절의 12개 규칙을 순서대로 적용해 MCP 호출 전 거부한다.
    통과한 SQL 문자열을 그대로 반환."""


# app/services/agent_service.py — Contract 불변조건을 구조로 강제하는 Discriminated Union
_RejectedCode = Literal[
    "invalid_request", "intent_contract_violation", "metadata_not_found",
    "query_plan_invalid", "sql_rejected",
]
_FailedCode = Literal["llm_unavailable", "mcp_execution_failed", "internal_error"]

class BoundedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_ms: int

class CompletedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correlation_id: str
    status: Literal["completed"] = "completed"
    bounded_result: BoundedResult

class ClarificationRequiredOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correlation_id: str
    status: Literal["clarification_required"] = "clarification_required"
    code: Literal["clarification_required"] = "clarification_required"
    message: str  # trim 후 비어 있지 않음(공통 validator)

class RejectedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correlation_id: str
    status: Literal["rejected"] = "rejected"
    code: _RejectedCode
    message: str  # trim 후 비어 있지 않음(공통 validator)

class FailedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correlation_id: str
    status: Literal["failed"] = "failed"
    code: _FailedCode
    message: str  # trim 후 비어 있지 않음(공통 validator)

QuestionOutcome = Annotated[
    CompletedOutcome | ClarificationRequiredOutcome | RejectedOutcome | FailedOutcome,
    Field(discriminator="status"),
]

async def handle_question(
    question: str,
    correlation_id: str,
    llm_client: LLMClient,
    mcp_client_manager: MCPClientManager,
    physical_metadata_catalog: PhysicalMetadataCatalog,
) -> QuestionOutcome:
    """RuntimeIntent -> Metadata Context -> QueryPlan -> SQL -> MCP 실행 순서로 호출하고
    각 단계의 예외를 Contract status/code로 변환한다. 예외를 상위로 전파하지 않는다."""


# app/services/metadata_service.py
class BusinessMetadataMappingError(RuntimeError): ...

def validate_physical_mapping(catalog: PhysicalMetadataCatalog) -> None:
    """레지스트리가 가정하는 Table·Column·FK가 실제 Catalog에 있는지 확인. 없으면
    BusinessMetadataMappingError(Startup 전파, Fail Closed)."""


# app/api/query.py
class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str  # 빈 문자열은 field_validator가 거부

router: APIRouter  # POST /api/questions
_QUESTION_API_PATH: str  # "/api/questions"

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    """request.url.path가 /api/questions가 아니면 fastapi.exception_handlers의
    request_validation_exception_handler(별칭 import)로 위임한다. /api/questions면
    새 Correlation ID를 발급해 rejected/invalid_request Contract 응답(422)으로 변환한다."""
```

Private Helper(Prompt 문자열 구성, Alias·정규식 매칭 내부 구현)는 고정하지 않는다.

## 동작과 데이터 흐름

`main.py`가 `app.add_exception_handler(RequestValidationError, query.validation_exception_handler)`를 등록한다. 이 Handler는 모든 Router에 전역으로 걸리지만 내부에서 `request.url.path == "/api/questions"`인 경우에만 Contract 응답으로 변환하고, 그 외 경로(`/health` 등 현재·향후 Router)는 `fastapi.exception_handlers.request_validation_exception_handler`를 별칭(`default_request_validation_exception_handler`)으로 import해 그대로 위임한다 — 이름 충돌 없이 FastAPI 기본 검증 오류 형식을 그 경로들에서 그대로 유지한다.

`POST /api/questions`에 대해 FastAPI가 `QuestionRequest`로 Body를 바인딩하는 과정(JSON 파싱, 필드 타입, `extra="forbid"`, 빈 질문 거부)에서 하나라도 실패하면 Router 함수는 호출되지 않고 위 Handler가 새 Correlation ID를 발급해 `rejected`/`invalid_request` 응답(422)을 반환한다. Body 검증을 통과한 요청만 Router 함수에 도달하며, 이때 Router가 별도로 Correlation ID를 발급해 `agent_service.handle_question()`을 호출한다. `mcp_client_manager`·`physical_metadata_catalog`·`llm_client`는 FastAPI `Depends`로 각각 `request.app.state`에서 가져와 전달한다.

`handle_question()` 내부 순서: `await intent_resolver.generate_runtime_intent()` → `requires_clarification=true`면 `clarification_required`로 즉시 반환 → `metadata_retriever.retrieve()` → `context_builder.build()` → `await query_planner.generate_query_plan()` → `plan_validator.validate()` → `await sql_generator.generate_sql()` → `sql_guardrail.validate()` → `mcp_client_manager.execute_readonly_query(sql, parameters=[], correlation_id, query_timeout_seconds=QUERY_TIMEOUT_SECONDS, maximum_returned_rows=MAXIMUM_RETURNED_ROWS)`. 각 단계는 실패하면 해당 단계의 예외만 던지고 이후 단계를 호출하지 않는다. `handle_question()`은 이 예외들을 모두 잡아 `QuestionOutcome`으로 변환하므로 Router 밖으로 예외가 나가지 않는다.

`QUERY_TIMEOUT_SECONDS=10`, `MAXIMUM_RETURNED_ROWS=100`은 `agent_service.py`의 모듈 상수다. 둘 다 FEAT-0003 Tool 입력 허용 범위(1~15초, 1~500행) 안이며, DB Query Timeout을 MCP Call Timeout(20초)보다 작게 유지한 FEAT-0003 원칙을 따른다. `QueryPlan.limit`은 `plan_validator`가, 생성된 SQL의 `TOP` 값은 `sql_guardrail`이 각각 `1`~`MAXIMUM_RETURNED_ROWS` 범위를 확인한다.

## 오류·보안·경계 처리

**LLM 설정은 Startup을 막지 않는다.** `LLM_PROVIDER`/`LLM_MODEL`/`LLM_API_KEY`가 없거나 Provider 규칙을 어겨도 ASGI Startup은 정상 완료된다(위 "LLM Client Wrapper와 내부 Instance의 Lifecycle 분리" 참고). 이 실패는 자연어 질문 API가 실제로 호출되는 시점에만 `failed`/`llm_unavailable`로 나타난다. `llm_client.py`는 설정 누락·규칙 위반, `openai.AuthenticationError`/`RateLimitError`/`APIConnectionError`/`APIStatusError`/`APITimeoutError`, `asyncio.timeout(20)` 초과를 모두 `LLMUnavailableError`로 통일하고 원문 메시지·API Key를 포함하지 않는다. 호출은 성공했지만 응답이 유효한 JSON이 아니거나 Contract를 만족하지 않으면 `LLMUnavailableError`가 아니라 해당 단계의 Contract 위반으로 처리한다.

**Backend SQL 최소 검증(`sql_guardrail.validate()`, MCP 호출 전 적용)**: 하나라도 위반하면 `SqlRejectedError`다.

1. 앞뒤 공백 제거, 끝의 세미콜론 하나까지만 제거. 그 뒤에도 `;`가 남으면 거부(다중 Statement).
2. 홑따옴표(`'`)가 하나라도 포함되면 거부한다 — Week 1 대표 질문은 문자열 Literal이 필요 없으므로 파싱·마스킹하지 않고 통째로 Fail Closed 한다. 향후 문자열 조건이 필요해지면 FEAT-0006의 Parser 기반 Guardrail 범위에서 지원 여부를 검토한다.
3. `--` 또는 `/*`가 포함되면 거부(주석).
4. 대소문자 무시 단어 경계로 `SELECT`의 개수를 세어 정확히 1개가 아니면 거부(Subquery·`UNION`의 두 번째 `SELECT` 포함 차단).
5. `^\s*SELECT\b`로 시작하지 않으면 거부. 나머지 위치에서 `WITH`·`INSERT`·`UPDATE`·`DELETE`·`MERGE`·`EXEC`·`EXECUTE`·`DROP`·`ALTER`·`CREATE`·`TRUNCATE`·`GRANT`·`REVOKE`·`INTO`·`UNION`·`EXCEPT`·`INTERSECT` 중 하나라도 단어 경계로 발견되면 거부.
6. `SELECT` 다음 토큰이 `TOP\s*\(?\s*(\d+)\s*\)?`와 일치하지 않으면 거부(TOP 부재). 추출한 정수가 `1`~`MAXIMUM_RETURNED_ROWS`(100) 밖이면 거부.
7. `*` 토큰이 SQL 어디에라도 남아 있으면(SELECT 목록 안 위치, `alias.*` 형태 포함) 거부한다 — Week 1은 곱셈이나 `COUNT(*)`가 필요 없으므로 위치와 무관하게 모든 `*`를 거부한다(규칙 2로 문자열 Literal이 이미 없으므로 별도 마스킹이 필요 없다).
8. `FROM`/`(INNER|LEFT)?\s*JOIN` 뒤의 Table 참조를 모두 추출한다. 각각이 `(Production\.)?Product` 또는 `(Production\.)?ProductInventory`(대괄호 표기 `[Production].[Product]` 포함) 중 하나와 일치하지 않으면 거부.
9. Table Alias는 `AS` 키워드를 사용한 선언(`Production.Product AS p`)만 허용한다. Table 참조 바로 뒤에 `AS` 없이 식별자가 오면 거부한다(암묵적 Alias 금지). `AS` 뒤 식별자를 이 Table의 승인 Alias로 기록한다.
10. `AS` 뒤에 오는 식별자 중 규칙 9에서 Table Alias로 이미 분류되지 않은 나머지를 모두 출력 Column Alias로 먼저 분류한다(예: `SUM(pi.Quantity) AS CurrentInventory`의 `CurrentInventory`). 각각이 승인된 출력 Alias(`ProductID`, `Name`, `CurrentInventory`, `SafetyStockLevel` — [자연어 질문 API Contract](../../contracts/natural-language-query.md)의 `bounded_result` 예시와 동일한 이름) 중 하나와 정확히 일치하지 않으면 거부.
11. 규칙 9·10에서 Table Alias와 출력 Column Alias 분류를 마친 뒤, SQL 전체에서 식별자 토큰(`[A-Za-z_][A-Za-z0-9_]*`, 대괄호로 감싼 형태 포함)을 모두 추출한다. 다음 어디에도 속하지 않는 토큰이 있으면 거부: SQL 예약어·집계 함수(`SELECT, FROM, JOIN, INNER, LEFT, ON, WHERE, GROUP, BY, HAVING, ORDER, ASC, DESC, TOP, AS, AND, OR, NOT, IN, IS, NULL, SUM, COUNT, AVG, MIN, MAX`), 규칙 8의 허용 Table 이름과 `Production` Schema 토큰, 규칙 9의 Table Alias, 규칙 10에서 승인된 출력 Column Alias, Allowlist 원본 Column(대소문자 무시 `ProductID`, `Name`, `SafetyStockLevel`, `Quantity`).
12. `ORDER BY` 자체가 없으면 거부. `ORDER BY` 바로 다음 첫 정렬 키가(선택적 Schema·Table·Alias 접두사와 대괄호 표기를 허용하며) `ProductID ASC`와 일치하지 않으면 거부.

통과한 SQL을 `mcp_client_manager.execute_readonly_query()`에 그대로 전달한다. `sql_generator.py`의 Prompt는 이 규칙과 일치하도록 항상 `AS`로 Table Alias를 선언하고 위 4개 출력 Alias만 사용하며 문자열 Literal을 사용하지 않도록 지시한다.

**Backend 검증과 MCP 재검증의 책임 구분**: `mcp_server/readonly_query_executor.py`의 SELECT-only·단일 Statement·금지 키워드 재검증은 제거하지 않고 그대로 유지한다. Backend(`sql_guardrail.py`)와 MCP Server는 SELECT-only·단일 Statement·금지 키워드를 각자 독립적인 신뢰 경계에서 의도적으로 중복 검증한다 — Backend는 Business Metadata를 알고 있어 Table·Column·Alias Allowlist·TOP 상한·정렬까지 추가로 검사하고, MCP Server는 그 지식이 없는 마지막 방어선으로 최소 안전성만 재확인한다(ADR-0007). 어느 한쪽도 다른 쪽의 대체물이 아니며, Backend 검증이 우회되거나 버그가 있어도 MCP Server가 최종 방어선 역할을 한다.

**단계별 예외 → Contract 매핑**은 `agent_service.py` 한 곳에서만 수행한다: `IntentContractViolationError`→`rejected/intent_contract_violation`, `requires_clarification=true`→`clarification_required/clarification_required`, `MetadataNotFoundError`→`rejected/metadata_not_found`, `QueryPlanInvalidError`→`rejected/query_plan_invalid`, `SqlRejectedError`→`rejected/sql_rejected`, `LLMUnavailableError`→`failed/llm_unavailable`, `MCPToolExecutionError`/`MCPTransportError`(기존 FEAT-0003 예외 재사용)→`failed/mcp_execution_failed`, 그 외 모든 예외→`failed/internal_error`. `QuestionOutcome`의 각 Model이 `code`를 Contract가 정의한 값만 갖는 `Literal`로 제한하므로(공개 경계 참고) 이 매핑 밖의 `code`나 잘못된 필드 조합은 Pydantic 검증에서 그 자체로 거부된다. MCP 실행 실패 시 대상 DB 직접 실행으로 우회하지 않는다.

**HTTP 상태 코드**(Contract가 고정하지 않은 Plan 결정): `completed`→200, `clarification_required`→200, `rejected`→422, `failed`→500. `status`가 이미 응답 본문에 있으므로 Client는 `status`/`code`를 기준으로 판단해야 한다.

Golden Query는 테스트에서만 존재하며 `sql_generator.py`는 모든 요청에서 항상 LLM을 호출한다 — 질문 문자열을 SQL로 직접 매핑하는 코드 경로를 만들지 않는다.

## 테스트 전략

**Fake 기반 단위·통합 테스트**(Docker MSSQL·실제 LLM 불필요): `tests/conftest.py`의 `FAKE_INSPECT_SCHEMA_RESULT`를 `Production.Product`(`ProductID`, `Name`, `SafetyStockLevel`)와 `Production.ProductInventory`(`ProductID`, `Quantity`) 두 Table, 둘 사이 Physical FK, 갱신된 PK 정보로 확장해 새 `validate_physical_mapping()` Startup 검증을 Fake로도 통과시킨다. 이 확장이 없으면 이 검증을 거치는 `fake_mcp_lifespan`을 쓰는 기존 FEAT-0001~0003 테스트(`test_health.py`, `test_admin_db_lifecycle.py`, `test_app_lifecycle.py` 등)가 모두 Startup 단계에서 실패하므로, 확장 직후 이 회귀가 없는지 전체 테스트로 확인한다. `LLMClient` Protocol을 구현하는 `FakeLLMClient`(요청 Prompt 기록, 미리 정의한 RuntimeIntent/QueryPlan/SQL JSON 반환, 오류 주입 모드로 `LLMUnavailableError` 시뮬레이션)를 추가하고 `agent_service`·`intent_resolver`·`query_planner`·`sql_generator`가 이를 명시적으로 주입받게 한다(모듈 전역 Monkeypatch 없음). `sql_guardrail.py`는 위 12개 규칙 각각의 위반 사례(다중 Statement, 문자열 Literal 포함, 주석, 금지 키워드, TOP 부재·상한 초과, 위치 무관 모든 `*`, `AS` 없는 Alias, 미승인 Table·Column·출력 Alias, `ORDER BY` 부재·비결정적 정렬)와 `SUM(pi.Quantity) AS CurrentInventory`를 포함한 정상 Aggregate SQL 통과 사례를 개별 테스트로 검증한다. `agent_service.py`는 Spec 실패 표의 각 분기를 결정적으로 검증한다. `app/services/agent_service.py`의 `RejectedOutcome`/`FailedOutcome`은 Contract 밖 `code` 값이나 `completed`에 `code`가 섞이는 등 잘못된 필드 조합이 Pydantic `ValidationError`로 거부되는지 확인한다.

**`/api/questions` 전용 Validation Handler 범위**: `app/api/query.py`는 `TestClient`로 `question` 누락·빈 문자열·비문자열 타입, 추가 필드, 비Object Body, malformed JSON이 모두 Correlation ID를 포함한 `rejected/invalid_request` 응답(422)으로 변환되는지 검증한다. 동시에 `/health`(또는 검증 오류를 일으키는 다른 경로)에 대해서는 같은 종류의 Body 오류가 FastAPI 기본 검증 오류 형식 그대로 유지되는지 확인해 전역 Handler가 `/api/questions` 밖에는 영향을 주지 않음을 증명한다.

**`requires_llm` 실행 조건과 Skip**: `tests/conftest.py`의 `pytest_collection_modifyitems` Hook은 `requires_llm`이 붙은 테스트를 `os.environ.get("RUN_LLM_TESTS") == "1"`이고 `llm_client.is_configured()`가 `True`인 두 조건을 모두 만족할 때만 실행하며, 하나라도 아니면 고정 Reason(설정값·Provider·모델·API Key·Base URL 미포함)으로 `pytest.mark.skip`을 부여한다 — `.env`에 유효한 LLM 설정이 있어도 `RUN_LLM_TESTS=1` 없이 일반 `pytest`를 실행하면 실제 LLM을 호출하지 않는다. `RUN_LLM_TESTS`는 테스트 실행 제어용 환경변수일 뿐이므로 `app/core/config.py`의 `Settings`나 `.env.example`에 추가하지 않고 이 Hook에서만 `os.environ`으로 직접 읽는다. `is_configured()` 재사용으로 실제 동작과 Skip 판단이 어긋나지 않는다. 이 Hook은 `requires_llm`에만 적용하며 기존 `requires_target_db`의 동작(`-m requires_target_db`로 선택 실행)은 바꾸지 않는다. Fake 기반 테스트와 기존 FEAT-0001~0003 테스트는 이 플래그와 무관하게 항상 실행되며 LLM 환경변수 없이도 통과해야 한다.

**실제 Docker MSSQL 검증**(`requires_target_db` marker, 기존 재사용): `metadata_service.validate_physical_mapping()`이 실제 Catalog로 통과하는지, `sql_guardrail`을 통과한 실제 생성 SQL이 `execute_readonly_query`로 실행되는지 확인한다.

**Golden Query와 표현 변형 검증**(`requires_target_db`+`requires_llm` 함께 적용, 위 두 조건 중 하나라도 없으면 Hook으로 자동 Skip): Golden SQL과 대표 정상 SQL 모두 문자열 Literal을 사용하지 않는다(Week 1 Guardrail이 문자열 Literal을 Fail Closed로 거부하므로 규칙 2에 걸린다). Golden SQL 문자열은 사람이 검토해 테스트 코드에 고정하지만, 그 결과는 하드코딩하지 않는다 — 테스트 실행마다 `execute_readonly_query` MCP Tool로 Golden SQL을 새로 조회해 비교 기준을 얻는다(어떤 코드도 `pyodbc`로 대상 DB에 직접 연결하지 않는다). 대표 질문과 한국어 표현 3종을 실제 파이프라인(실제 LLM)으로 실행해 반환된 `bounded_result`의 제품 집합·`ProductID` 순서·재고·안전재고 값이 이 기준과 일치하는지 비교한다 — 생성된 SQL 문자열 자체는 비교 대상이 아니다. 실제 Provider·모델이 아직 `.env`에 준비되지 않은 것은 이 Plan의 미결정 사항이 아니지만, 이 비교 없이는 Feature를 완전히 완료된 것으로 보고할 수 없다. 구현 완료 검증 시 `RUN_LLM_TESTS=1`을 명시해 실행하고, 실제로 사용한 Provider·모델명만 `tasks.md`에 기록하며 API Key는 기록하지 않는다.

**Secret·원문 오류 비노출**: `LLMUnavailableError`/`MCPToolExecutionError` 메시지와 `requires_llm` Skip Reason에 API Key나 Provider 원문 오류 문자열이 포함되지 않는지 Marker 문자열 방식(FEAT-0003과 동일한 패턴)으로 확인한다.

## 요구사항 추적

| 요구사항 | Plan 설계 | 검증 |
|---|---|---|
| `FR-001` | Handler 또는 Router가 Correlation ID 발급, `agent_service`가 전 단계에서 재사용 | `test_api_query.py`, `test_agent_service.py` |
| `FR-002` | `llm_client`가 `.env`로 읽은 4개 설정 규칙을 검증, 실패 시 `LLMUnavailableError` | `test_llm_client.py`, `test_agent_service.py`(설정 없음 분기) |
| `FR-003` | `intent_resolver`가 RuntimeIntent Contract 검증, 위반·명확화 시 이후 단계 미호출 | `test_intent_resolver.py`, `test_agent_service.py` |
| `FR-004` | `metadata_service.py` 정적 레지스트리(재고 모집단 정의·Alias 포함) + Startup `validate_physical_mapping()`(확장된 Fake Catalog로 검증) | `test_metadata_service.py`, Docker 검증 |
| `FR-005` | `metadata_retriever.retrieve()`가 Alias 규칙으로 Demo Scope 밖·Metadata 없음을 `MetadataNotFoundError`로 거부 | `test_metadata_retriever.py`, `test_agent_service.py` |
| `FR-006` | `query_planner`+`plan_validator`가 참조 ID·`depth=1`·Demo Scope를 검증 | `test_query_planner.py`, `test_plan_validator.py` |
| `FR-007` | `sql_guardrail`의 12개 규칙이 MCP 호출 전 SELECT-only·문자열 Literal 거부·Allowlist·Alias·TOP·`ORDER BY`를 검증 | `test_sql_guardrail.py` |
| `FR-008` | `agent_service`가 `mcp_client_manager.execute_readonly_query()`만 호출, 기본 정렬은 `plan_validator`+`sql_guardrail` 규칙 12가 이중 강제 | `test_agent_service.py`, Docker 검증 |
| `FR-009` | 각 서비스 함수가 자신의 Contract만 검증해 반환하고 다음 단계는 그 반환값만 사용 | 각 단위 테스트, 코드 리뷰 |
| `FR-010` | Golden SQL 고정 + 매 실행 시 MCP로 재조회한 기준 + 표현 변형 3종 + End-to-End 파이프라인 | Golden Query 비교 테스트(`requires_target_db`+`requires_llm`) |
| `NFR-001` | `agent_service`는 `MCPClientManager`만 호출, 대상 DB Driver 미사용 | 코드 리뷰 |
| `NFR-002` | `llm_client.py`가 단일 Client 구현체만 제공, Provider 값에 따른 SDK 분기 없음 | 코드 리뷰 |
| `NFR-003` | `sql_generator`는 항상 LLM 호출, 고정 SQL 매핑 코드 없음, Backend Guardrail은 Week 1 최소 검증(정규식)만 수행하고 AST Parser 미도입 | `test_agent_service.py`, 코드 리뷰 |
| `NFR-004` | 모든 예외 변환이 고정 메시지만 사용, 원문·Secret 미노출, Skip Reason도 동일 원칙 | Secret 비노출 테스트 |
| `NFR-005` | `mcp_client_manager` 재사용, 새 MCP 경계 미구현, LLM 미설정이 Startup 실패를 일으키지 않음 | 기존 FEAT-0001~0003 테스트 회귀 확인(확장된 Fake Catalog 포함) |

Spec Acceptance Criteria는 위 각 행의 설계·검증으로 충족되며 별도 표로 반복하지 않는다.

## 미결정 사항

없음. `.env` 로딩과 FastAPI/MCP Settings 분리, `/api/questions` 전용 Validation Handler와 기본 Handler 위임, LLM Client Wrapper·내부 Instance Lifecycle(설정 변경 후 재시작 필요 포함)과 전체 Timeout 의미, `max_completion_tokens` 명명, 응답 `code` Enum과 `extra="forbid"` 불변조건, Backend SQL 12개 규칙(문자열 Literal 거부, Alias·출력 Alias 분류 순서 포함), `requires_llm`의 `RUN_LLM_TESTS`+`is_configured()` 이중 조건, Fake Physical Catalog 확장을 포함해 구현 범위·공개 경계·검증에 영향을 주는 기술 결정을 모두 이 Plan에서 확정했다. 실제 LLM Provider·모델이 아직 `.env`에 준비되지 않은 것은 실행 환경 설정 문제이며 Plan 미결정 사항이 아니다(테스트 전략의 Golden Query 절 참고).

## 검토 기록

| Reviewer | 발견 사항 | 심각도 | 결정과 근거 | 상태 |
|---|---|---|---|---|
| Codex | Backend가 MCP 호출 전 SELECT-only 등 최소 SQL 검증을 하지 않고 MCP Server에만 의존해 FR-007과 어긋남 | High | `sql_guardrail.py`에 11개 규칙을 정규식·토큰 기반으로 확정, MCP 재검증은 독립된 추가 방어 계층으로 유지 | Resolved |
| Codex | 동기 `OpenAI` Client가 FastAPI Event Loop를 막을 위험, Timeout·Retry·Token 상한 미확정 | High | `AsyncOpenAI`(`openai>=2.8,<3`)와 `async def`로 전환, Timeout 20초·Retry 1회·Token 상한(500/800/600) 확정 | Resolved |
| Codex | Plan에서 실제 Provider·모델을 고정하거나 `LLM_PROVIDER`를 완전히 무시하는 구조를 피해야 함 | Medium | `LLM_BASE_URL` 유무에 따른 `LLM_PROVIDER` 검증 규칙만 확정, 실제 값은 `.env` 실행 환경 설정으로 남김 | Resolved |
| Codex | `QuestionRequest(extra="allow")`만으로는 malformed JSON 등이 FastAPI 기본 422로 처리되어 Contract 응답이 누락되고, `QuestionOutcome`의 모든 필드가 Optional이라 불변조건이 강제되지 않음 | High | `extra="forbid"`+`field_validator`, 전용 `RequestValidationError` Handler, `status` Discriminator 기반 Union 4종으로 재정의 | Resolved |
| Codex | Plan이 `FakeLLMClient` 사용을 언급하지만 공개 경계에 LLM Client 주입 경로가 없어 Monkeypatch에 의존 | Medium | 최소 `LLMClient` Protocol을 정의하고 4개 서비스가 이를 인자로 주입받도록 통일, `requires_llm`은 Collection Hook으로 자동 Skip | Resolved |
| Codex | Metadata 검색 Alias 매칭 규칙이 Private Helper로만 남아 구현 시 임의 확장 위험 | Medium | Entity·Concept별 승인 Alias 목록과 매칭·실패 조건을 명시 | Resolved |
| Codex | Golden Query 기준 결과를 얻는 경로가 대상 DB 직접 연결을 배제한다는 점이 명시되지 않음 | Medium | Golden SQL은 고정하되 기준 결과는 매 테스트 실행 시 MCP Tool로 재조회하도록 확정 | Resolved |
| Codex | FastAPI `Settings`가 저장소 루트 `.env`를 읽지 않아 구현 전 준비한 LLM 설정을 인식하지 못할 위험, `requires_llm` Skip이 `os.environ`만 보면 실제 동작과 어긋날 위험 | High | `Settings`에 `SettingsConfigDict(env_file=REPO_ROOT/".env")` 추가(`TARGET_DB_*` 소유권은 불변), `is_configured()`를 Skip Hook과 공유해 단일 판단 경로로 통일 | Resolved |
| Codex | 전역 `RequestValidationError` Handler가 `/health` 등 다른 Router의 검증 오류까지 자연어 질문 Contract로 바꿀 위험 | High | Handler 내부에서 `request.url.path == "/api/questions"`로 분기하고 그 외는 `fastapi.exception_handlers.request_validation_exception_handler`로 위임(별칭 import로 이름 충돌 회피), 경로별 테스트 추가 | Resolved |
| Codex | LLM Wrapper와 내부 `AsyncOpenAI` 생성 시점이 문서 안에서 혼용되고, Timeout 20초가 Retry 포함 전체 상한인지 불명확, Token Parameter 이름이 실제 SDK 의미와 다름 | Medium | Wrapper=Startup에 즉시 생성(검증 없음)/내부 Instance=첫 호출에 지연 생성이라는 2단 Lifecycle을 명시하고, `asyncio.timeout(20)`으로 Retry 포함 전체 호출을 제한, Protocol 인자명을 `max_completion_tokens`로 통일 | Resolved |
| Codex | `RejectedOutcome`/`FailedOutcome.code`가 단순 `str`이라 Contract 밖 값을 허용하고 추가 필드 금지가 없음 | Medium | 두 Model의 `code`를 Contract `code` 값만 갖는 `Literal`로 제한, 4개 Outcome Model과 `BoundedResult` 모두 `extra="forbid"`, `message` 비어있지 않음 검증 추가, 관련 Pydantic 검증 테스트 추가 | Resolved |
| Codex | Wildcard 검사가 SELECT 목록 첫 토큰만 봐 `SELECT TOP (100) p.ProductID, p.*` 같은 우회 가능, Alias·출력 Alias·문자열 Literal 처리 기준 부재, "Backend가 SELECT-only를 재구현하지 않는다"는 문장이 실제 설계와 모순 | Medium | SQL 전체에서 모든 `*` 거부, `AS` 선언 Table Alias만 허용, 승인 출력 Alias 4종만 허용, 문자열 Literal 마스킹 후 토큰 검사(11개 규칙 9·10), Backend·MCP 중복 검증 문장으로 통일 | Resolved |
| Codex | 새 Startup의 `validate_physical_mapping()`이 기존 `FAKE_INSPECT_SCHEMA_RESULT`(Product.SafetyStockLevel·ProductInventory·FK 없음)로 통과할 수 없어 기존 Health·Admin DB·MCP 테스트가 깨질 위험 | Medium | `tests/conftest.py`의 Fake Catalog를 FEAT-0004 최소 물리 매핑과 일치하도록 확장하고, 확장 직후 기존 FEAT-0001~0003 테스트 전체 회귀 확인을 테스트 전략에 명시 | Resolved |
| Codex | SQL Guardrail 규칙 9가 전체 식별자를 먼저 검사하고 규칙 10에서 출력 Alias를 나중에 분류해, `SUM(pi.Quantity) AS CurrentInventory` 같은 정상 대표 SQL의 `CurrentInventory`가 Allowlist를 통과하지 못함 | Medium | Table Alias·출력 Column Alias 분류(신규 규칙 9·10)를 전체 식별자 Allowlist 검사(규칙 11)보다 먼저 수행하도록 순서를 교정하고, `SUM(pi.Quantity) AS CurrentInventory` 통과 회귀 테스트를 테스트 전략에 명시 | Resolved |
| Codex | 문자열 마스킹 후 검사한다면서도 테스트 전략은 문자열 안 예약어·`*`의 오탐 방지를 요구해 설계가 서로 모순됨 | Medium | Week 1 Guardrail은 홑따옴표 문자열 Literal 자체를 신규 규칙 2로 Fail Closed 거부하고 마스킹 로직을 제거, 문자열 Literal 포함 SQL이 거부되는 테스트로 교체, Golden Query·대표 SQL은 문자열 Literal을 쓰지 않는다고 명시, 향후 지원은 FEAT-0006 Parser 범위로 경계만 남김 | Resolved |
| Codex | `.env`에 유효한 LLM 설정이 있으면 일반 `pytest` 실행에서도 `requires_llm` 테스트가 실제 LLM을 호출해 의도치 않은 외부 호출·비용·불안정성을 만들 위험 | Medium | `requires_llm` 실행 조건을 `RUN_LLM_TESTS=1`과 `is_configured()`가 모두 참인 경우로 좁히고(둘 중 하나라도 아니면 고정 Reason으로 Skip), `RUN_LLM_TESTS`는 애플리케이션 Settings·`.env.example`에 추가하지 않고 테스트 Hook에서만 읽도록 명시. LLM Client Lifecycle에 내부 Instance 생성 후 `.env` 변경은 애플리케이션 재시작이 필요하다는 문장 추가 | Resolved |
| Codex | Approved Plan이 확정한 Token 상한(RuntimeIntent 500/QueryPlan 800/SQL 600)이 구현 단계에서 실제 값(2000/3000/2000)과 어긋난 채로 tasks.md에만 "구현 세부사항"으로 잘못 기록되어 있었음 — Plan 문서 자체는 갱신되지 않음 | Medium | "기술적 접근" 절의 확정값을 실제 구현값(2000/3000/2000)과 그 변경 근거(숨겨진 reasoning Token으로 인한 응답 절단 관찰, 비용·지연 증가 가능성)로 동기화. Codex 재검토에서 구현값·관찰 기록과 일치하며 공개 Contract·보안 경계를 바꾸지 않는 합리적인 조정임을 확인했다. Plan의 `Approved` 변경은 사용자 결정으로 남긴다 | Codex 재검토 완료, 사용자 승인 대기 |

## Plan 승인 조건

* [x] Source Spec에 Development Track이 있으면 해당 Track의 문서화 수준을 적용함
* [x] Approved Spec의 모든 요구사항을 추적함
* [x] ADR, Architecture와 Contract에 충돌하지 않음
* [x] 공개 경계, 실패 동작과 테스트 전략이 명확함
* [x] 추가 설계 결정 없이 구현을 시작할 수 있도록 변경 파일과 책임이 명확함
* [x] 기술 미결정 사항이 없음
* [x] 필수 Codex 검토 의견이 해결되거나 기각 근거가 기록됨(Token 상한 동기화 건 재검토 완료, 사용자 재승인 대기)
