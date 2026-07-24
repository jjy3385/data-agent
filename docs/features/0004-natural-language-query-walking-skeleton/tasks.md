# 자연어 질문 처리 최소 동작 흐름 (Walking Skeleton) Tasks

* Feature ID: `FEAT-0004`
* Status: `Verified`
* Development Track: `Standard`
* Source Spec: [`./spec.md`](./spec.md) (`Approved`)
* Source Plan: [`./plan.md`](./plan.md) (`Approved` — Token 상한 확정값(RuntimeIntent/QueryPlan/SQL)을 실제 구현값과 동기화한 뒤 사용자가 재승인함. 자세한 내용은 아래 "Codex 구현 재검토 발견 사항과 수정(2차)" 참고)

## 구현 요약

Approved Plan대로 `POST /api/questions`가 자연어 질문을 받아 Correlation ID 발급 → RuntimeIntent 생성·Contract 검증 → (명확화 필요 시 즉시 응답) → 고정 Demo Scope Business Metadata 검색·Metadata Context 구성 → Depth 1 QueryPlan 생성·구조/의미 검증 → MSSQL 생성 → Backend 12개 규칙 SQL Guardrail → FEAT-0003 `MCPClientManager.execute_readonly_query()` 순서로 실제로 연결되는 파이프라인을 구현했다. LLM은 `openai>=2.8,<3`의 `AsyncOpenAI`만 사용하는 단일 OpenAI 호환 경계(`OpenAICompatibleLLMClient`)로 접근하며, `LLM_PROVIDER`/`LLM_MODEL`/`LLM_API_KEY`/`LLM_BASE_URL`은 저장소 루트 `.env`(신규로 `app/core/config.py`가 읽음)에서만 가져온다. FastAPI는 어떤 코드 경로에서도 대상 DB에 직접 연결하지 않으며, LLM이 생성한 RuntimeIntent·QueryPlan·SQL은 각 단계에서 Backend가 검증한 뒤에만 다음 단계로 진행한다. LLM 설정 누락은 Startup을 막지 않고 요청 시점에 `failed/llm_unavailable`로 나타나며, Business Metadata와 Physical Metadata Catalog의 불일치는 Startup을 막는 Fail Closed로 구현했다.

**실제 Gemini(`gemini-3.6-flash`, OpenAI 호환 Endpoint)로 라이브 디버깅한 결과 두 가지 실제 동작 문제를 발견해 Prompt·Token 상한을 조정했다**(아래 "구현 중 발견 사항" 참고): (1) Gemini의 숨겨진 reasoning Token이 `max_completion_tokens` 예산을 소비해 Plan이 정한 원래 값(500/800/600)에서는 JSON이 중간에 잘렸다 → Token 상한을 2000/3000/2000으로 올렸다(이는 Approved Plan의 명시적 수치와 다른 구현 차이다 — 아래 "Codex 구현 검토 발견 사항과 수정(1차)"의 발견 5 참고). (2) LLM이 QueryPlan의 `filters`를 빈 배열로 생성해 안전재고 조건 없이 전체 제품을 반환하는 SQL이 만들어졌다 → QueryPlan Prompt에 filter 포함 규칙을 추가했지만, Prompt 지시만으로는 Backend 강제가 되지 않는다는 것이 이후 Codex 구현 검토에서 지적되어 `plan_validator.py`와 `sql_guardrail.py`에 실제 강제 검증을 추가했다(발견 1·2·3).

**Codex 구현 검토에서 발견된 5건을 이전 라운드에서 반영했고 후속 재검토를 완료했다**(발견 1~5는 아래 "Codex 구현 검토 발견 사항과 수정(1차)" 참고): (1) 고정 Demo Scope 필수 Filter·Metric·Join 의미가 `plan_validator.py`에서 강제되지 않던 문제를 실제 필수 집합 검증으로 수정, (2) Metadata ID가 존재하기만 하면 종류가 달라도 통과하던 문제를 kind별 검증으로 수정, (3) QueryPlan에서 Filter를 강제해도 생성 SQL 자체에서 안전재고 조건이 누락될 수 있던 문제를 `sql_guardrail.py`의 고정 Demo Scope 의미 검증으로 보강, (4) Golden Query E2E가 `Name`을 비교하지 않던 문제를 4개 필드 비교로 수정, (5) tasks.md의 Token 상한 Plan 차이 설명이 부정확했던 것을 정확한 설명으로 수정.

**Codex 재검토에서 추가로 발견된 3건도 반영하고 후속 확인을 완료했다**(자세한 내용은 아래 "Codex 구현 재검토 발견 사항과 수정(2차)" 참고): (1) `sql_guardrail.py`의 JOIN 검증이 Alias가 실제로 어떤 물리 Table을 가리키는지 확인하지 않아, 같은 Table을 다른 Alias로 중복 참조해 겉보기엔 정상인 Product-ProductInventory Join을 흉내 내면서 실제로는 무관한 비제약 Cross Join을 만드는 SQL이 통과할 수 있었다 — Table Alias를 `alias -> table` 매핑으로 관리하고 중복 Table·Alias 선언을 Fail Closed로 거부하도록 수정. (2) Approved Plan에 남아 있던 Token 상한 확정값(500/800/600)을 실제 구현값(2000/3000/2000)으로 동기화하고 사용자 재승인을 완료했다. (3) `llm_unavailable`로 뭉뚱그려진 LLM 실패 중 Rate Limit(할당량 초과)을 구분할 수 있도록 공개 `code`는 유지하면서 내부 `reason`과 전용 재시도 메시지를 추가했다.

**D·E·F 수정 라운드에서는 실제 Gemini API를 호출하지 않았지만, 모든 Codex 구현 발견을 해결한 뒤 최종 검증에서 실제 Gemini Golden Query E2E를 실행했다.** 첫 실행은 대표 질문 1건이 통과하고 표현 변형 2건이 Rate Limit으로 실패했으나, 잠시 뒤 재실행에서 세 질문 모두 `completed`로 Golden Query의 `ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel` 전체 결과와 일치했다. `TASK-013`을 `Completed`로 변경하고 Feature 완료 조건을 충족했다.

**Codex 최종 재검토 결과, 2차 수정 3건 자체는 의도대로 반영됐지만 SQL Guardrail에서 새로운 High 발견 2건이 재현됐다**(아래 "Codex 구현 최종 재검토 발견 사항(3차)" 참고): (1) 필수 ProductID Join 또는 안전재고 HAVING 조건 뒤에 `OR 1 = 1`을 붙여도 정규식이 정상 부분만 찾아 승인하므로 Join·Filter를 무력화할 수 있다. (2) 필수 출력 Alias의 존재만 확인하고 각 Alias가 승인된 물리 표현식에 정확히 연결됐는지 확인하지 않아 `pi.Quantity AS Name`처럼 의미가 잘못 라벨링된 결과가 통과한다. 따라서 1차 발견 3의 안전재고 조건 강제와 2차 발견 A의 JOIN 검증은 새 우회까지 막도록 추가 수정이 필요하며, 현재 구현 검토는 완료할 수 없다.

**3차 재검토 대응에서 발견 D·E를 모두 수정했고 Codex 4차 재검토에서 `Resolved`로 확인했다**(아래 발견 D·E와 "Codex 구현 최종 재검토 발견 사항(4차)" 참고): (1) 발견 D — `sql_guardrail.py`의 ON/HAVING 검증을 `.search()` 기반 부분 문자열 포함 확인에서 Clause 전체 정확 일치 비교로 재작성했다. (2) 발견 E — SELECT 목록을 정확히 4개의 승인된 출력 표현식으로 파싱해 각 출력 Alias가 승인된 물리 표현식과 정확히 연결되고 한 번씩만 선언되는지 확인하도록 수정했다. 다만 4차 재검토에서 GROUP BY 추가 Grain을 허용하는 새 High 발견 F가 재현됐다.

**이번 라운드에 발견 F를 수정했고 Codex 5차 재검토에서 `Resolved`로 확인했다**(아래 발견 F 항목 참고): `GROUP BY` Clause 전체(`GROUP BY` 바로 뒤부터 `HAVING` 직전까지)를 추출해 승인된 세 표현식(`<Product alias>.ProductID`/`Name`/`SafetyStockLevel`)만 정확히 한 번씩 나타나는지 확인하도록 수정했다. `GROUP BY` 키워드가 정확히 한 번만 나타나는지도 별도로 확인해 중복 Clause·부분 문자열 우회를 막았고, 세 표현식의 순서 변경·대괄호·Alias 대소문자는 계속 허용한다. 이번 라운드도 실제 Gemini API를 호출하지 않았다.

## 요구사항 Coverage

| Spec 요구사항 | Plan 절 | 실제 구현 Task | 검증 결과 |
|---|---|---|---|
| `FR-001` | 동작과 데이터 흐름 | `TASK-009` | 통과(Fake 기반 HTTP 테스트) |
| `FR-002` | 기술적 접근(.env 로딩, LLM SDK) | `TASK-001`, `TASK-002` | 통과(단위 테스트 + 실제 Gemini 연결 확인) |
| `FR-003` | 기술적 접근, 공개 경계 | `TASK-004` | 통과(단위 테스트 + 실제 Gemini RuntimeIntent 확인) |
| `FR-004` | Business Metadata 저장과 결합 | `TASK-003` | 통과(단위 테스트 + 실제 Docker DB `validate_physical_mapping`) |
| `FR-005` | Metadata 검색 Alias 규칙 | `TASK-005` | 통과(단위 테스트 + 실제 Gemini Alias 어휘 확인) |
| `FR-006` | QueryPlan 생성/검증 | `TASK-006` | 통과(단위 테스트 28건 — 고정 Demo Scope 필수 항목·종류별 검증 포함 + 실제 Gemini QueryPlan 1회 확인) |
| `FR-007` | Backend SQL 최소 검증 12개 규칙 + 고정 Demo Scope 의미 검증(JOIN Alias가 실제로 가리키는 Table까지 확인) | `TASK-007` | 통과(단위 테스트 62건 — JOIN/HAVING, 출력 Alias-표현식 결합, Product GROUP BY Grain 강제와 우회 거부 포함) |
| `FR-008` | MCP 실행, 기본 정렬 | `TASK-008`, `TASK-010` | 통과(Fake 기반 + 실제 Docker DB Golden Query 인프라) |
| `FR-009` | 오류·보안·경계 처리, SQL에서 안전재고 조건을 Backend가 검증 | `TASK-008`, `TASK-007` | 통과(코드 리뷰 + 단위 테스트) |
| `FR-010` | Golden Query·표현 변형(ProductID/Name/CurrentInventory/SafetyStockLevel 4개 필드 비교) | `TASK-013` | 통과(실제 Gemini+Docker MCP E2E 3건, Golden Query 4개 필드 전체 결과 일치) |
| `NFR-001` | MCP 경계만 사용 | 전체 | 통과(코드 리뷰 — `pyodbc` import는 `mcp_server/`에만 존재) |
| `NFR-002` | 단일 Provider | `TASK-002` | 통과(코드 리뷰) |
| `NFR-003` | 고정 SQL 매핑 금지, Week1 최소 검증(SQL Parser 미도입) | `TASK-007` | 통과(코드 리뷰 — `sql_generator`는 항상 LLM 호출, 정규식·토큰 기반 유지) |
| `NFR-004` | 원문 비노출(Rate Limit 등 내부 reason 포함) | `TASK-002`, `TASK-008` | 통과(단위 테스트 Secret Marker 확인, Rate Limit·빈 응답 원문 비노출 포함) |
| `NFR-005` | MCP 재사용, LLM 미설정이 Startup 안 막음 | `TASK-010` | 통과(기존 FEAT-0001~0003 포함 전체 308건 중 `requires_llm` 3건 제외 295건 Fake 기반 통과, Docker 필요 10건은 별도 확인) |

Spec Acceptance Criteria는 위 각 행의 설계·검증으로 충족되며 별도 표로 반복하지 않는다.

## `TASK-001` FastAPI Settings의 `.env` 로딩과 LLM 설정 필드

* Status: `Completed`
* 요구사항: `FR-002`
* 실제 변경 파일:
  * `app/core/config.py`

구현 결과:

* `Settings`에 `SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")`를 추가해 저장소 루트 `.env`를 읽는다(`mcp_server/db.py`의 `TargetDBSettings`와 동일한 패턴). `llm_provider`/`llm_model`/`llm_api_key`/`llm_base_url`(모두 선택, 기본값 `None`) 4개 필드를 기존 `app_env`/`admin_db_path`와 같은 클래스에 추가했다. `mcp_server/db.py`의 `TARGET_DB_*` 소유권과 로딩 방식은 그대로 두었다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_config.py tests/test_llm_client.py`
* 결과: 통과 — 기존 `test_config.py`(4개, `ADMIN_DB_PATH` 검증)가 회귀 없이 통과했고, `test_llm_client.py`가 `Settings(_env_file=None, ...)`로 실제 `.env`를 격리해 LLM 설정 규칙을 검증한다.

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-002` LLM Client 경계

* Status: `Completed`
* 요구사항: `FR-002`, `NFR-002`, `NFR-004`
* 실제 변경 파일:
  * `app/services/llm_client.py`

구현 결과:

* `LLMClient` Protocol(`complete_json`/`complete_text`, 둘 다 `max_completion_tokens` 필수 인자)과 `OpenAICompatibleLLMClient` 구현체를 만들었다. `__init__()`은 설정 검증이나 네트워크 호출을 하지 않는다(항상 성공). 첫 호출에서 `_ensure_client()`가 `LLM_BASE_URL` 유무에 따른 `LLM_PROVIDER` 규칙(없으면 정확히 `"openai"`, 있으면 비어있지 않은 임의 값)과 `LLM_MODEL`/`LLM_API_KEY` 필수 여부를 검증한 뒤 `AsyncOpenAI(timeout=20.0, max_retries=1)`를 지연 생성해 캐싱한다. 이후 호출은 캐시된 Instance를 재사용하고, 일시적 API 실패로 폐기하지 않는다. 각 호출은 `asyncio.timeout(20)`으로 SDK Retry를 포함한 전체 시간을 다시 제한한다. `openai.OpenAIError` 하위 예외와 Timeout은 모두 원문 없이 `LLMUnavailableError`로 변환한다. `is_configured()`는 같은 검증 로직을 재사용해 결과(`bool`)만 반환하며 `requires_llm` Skip Hook이 이를 그대로 사용한다. `aclose()`는 내부 Instance가 없으면 no-op, 있으면 1회 정리한다.
* Token 상한은 호출부(각 서비스 모듈)가 지정한다: 최초 Plan 값은 RuntimeIntent 500/QueryPlan 800/SQL 600이었으나, 실제 Gemini(`gemini-3.6-flash`)로 확인한 결과 숨겨진 reasoning Token이 예산을 먼저 소비해 `finish_reason: "length"`로 JSON이 중간에 잘리는 문제를 발견했다(`completion_tokens=20`인데 `total_tokens=861`처럼 보이지 않는 Token이 다수 소비됨). 2000/3000/2000으로 올려 실제 Gemini 응답이 `finish_reason: "stop"`으로 끝까지 나오는 것을 확인했다.
* **이번 라운드에 Codex 재검토 발견을 반영해 `LLMUnavailableError`에 내부 `reason` 속성을 추가했다.** 공개 Contract의 `code`(`llm_unavailable`)는 바꾸지 않고 새 공개 `code`도 추가하지 않았다 — `reason`은 Backend 내부에서만 쓰고 API 응답에는 노출하지 않는다. 값은 `configuration_error`(설정 누락·무효), `timeout`(전체 호출 Timeout), `rate_limited`(`openai.RateLimitError`), `provider_error`(그 외 `OpenAIError`, 기본값), `empty_response`(빈 응답) 5종이며, `openai.RateLimitError`를 `OpenAIError`보다 먼저 잡도록 `except` 순서를 정했다(`RateLimitError`가 `APIStatusError`→`APIError`→`OpenAIError`의 하위 클래스이므로 순서가 중요하다). 알려지지 않은 값이 들어와도 호출부가 깨지지 않도록 생성자 기본값을 `"provider_error"`로 뒀다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_llm_client.py`
* 결과: 통과 (15 passed — 이번 라운드에 3개 추가) — 설정 규칙(Provider/BaseURL 조합 5종, 각각 `reason="configuration_error"` 확인), 미설정 시 `LLMUnavailableError`, `aclose()` no-op, SDK 오류(`APIConnectionError`, `reason="provider_error"`)와 Timeout(`reason="timeout"`)이 Secret Marker 없이 변환됨, `RateLimitError`가 `reason="rate_limited"`로 변환되고 원문 미노출(신규), 빈 응답이 `reason="empty_response"`로 변환됨(신규), 기본 `reason` 값 확인(신규), 내부 Client 재사용(`is` 비교) 확인.
* 실제 Gemini 확인(수동, 이전 라운드): `complete_json`/`generate_runtime_intent`/`generate_query_plan`/`generate_sql`을 실제 `.env` 설정으로 호출해 연결·JSON Mode·Token 상한이 실제로 동작함을 확인했다(아래 "구현 중 발견 사항" 참고). 이번 라운드는 무료 할당량을 소비하지 않기 위해 실제 Gemini API를 호출하지 않았다(사용자 지침) — `reason` 분류는 Fake 기반 테스트로만 확인했다.

Plan과의 차이:

* **Approved Plan의 명시적 Token 상한(RuntimeIntent 500, QueryPlan 800, SQL 600)과 다른 구현 세부사항이었다.** Plan은 "기술적 접근" 절에 "RuntimeIntent 500, QueryPlan 800, SQL 600"이라는 정확한 수치를 확정했었다(이전 라운드 tasks.md는 이를 "Plan이 정확한 수치를 고정하지 않았다"고 잘못 설명했으며 Codex 구현 검토 발견 5에 따라 정정했다). 실제 Gemini(`gemini-3.6-flash`)에서 숨겨진 reasoning Token 때문에 RuntimeIntent JSON과 SQL 응답이 원래 상한에서 중간에 잘리는 현상(`finish_reason: "length"`)을 실제로 관찰해 2000/3000/2000으로 올렸다. 공개 Contract, 대상 DB 접근 경계, 보안 경계는 변경하지 않았다. 호출당 Token 예산이 늘어난 만큼 요청당 비용과 지연이 증가할 가능성이 있다. **이번 라운드에 이 차이를 해소했다** — `plan.md`의 확정값을 실제 구현값(2000/3000/2000)으로 동기화하고 변경 근거를 Plan 본문에 직접 기록했다. Approved Plan의 확정값을 바꾸는 변경이므로 `plan.md`를 임의로 다시 `Approved` 처리하지 않고 `Draft`로 되돌려 Codex 재검토를 기다린다(아래 "Codex 구현 재검토 발견 사항과 수정(2차)" 참고).
* `LLMUnavailableError`에 `reason` 키워드 인자를 추가했다. Plan은 이 예외를 "원문 오류를 노출하지 않는 안전한 예외로 변환한다"는 원칙만 정의했고 예외의 정확한 속성 구성은 구현 세부사항으로 남겼으므로, 공개 Contract의 `code`나 `agent_service`의 예외 매핑 대상 타입 자체는 바뀌지 않는 이 추가는 Plan 재승인 없이 진행했다.

Reviewer 의견과 처리:

* 미검토

## `TASK-003` Business Metadata 레지스트리와 Physical Mapping 검증

* Status: `Completed`
* 요구사항: `FR-004`
* 실제 변경 파일:
  * `app/services/metadata_service.py`
  * `app/core/lifespan.py`(일부, `TASK-010`과 공유)

구현 결과:

* `app/services/metadata_service.py`에 정적 레지스트리(Entity 1, Dimension 2, Metric 2, Filter 1, Grain 1, Join 1 — 총 8개 `MetadataEntry`)를 만들었다. 각 항목은 `sql_hint`(물리 Table·Column·집계·Join·Filter 표현)와 `description`을 갖는다. `current_inventory`의 `description`에 "ProductInventory 행이 없는 제품은 모집단에서 제외하며 재고 0 값을 생성하거나 비교하지 않는다"를 명시해 FR-004의 재고 정의를 그대로 반영했다.
* `validate_physical_mapping(catalog)`가 `Production.Product`(`ProductID`/`Name`/`SafetyStockLevel`)와 `Production.ProductInventory`(`ProductID`/`Quantity`) Table·Column 존재, 그리고 `ProductInventory.ProductID -> Product.ProductID` Physical FK 존재를 확인한다. 하나라도 없으면 `BusinessMetadataMappingError`를 던지며, `app/core/lifespan.py`가 이를 잡지 않고 그대로 전파해 ASGI Startup을 완료시키지 않는다(Fail Closed).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_metadata_service.py`
* 결과: 통과 (5 passed) — 레지스트리 8개 항목의 kind별 유일성, 확장된 Fake Catalog로 통과, Table 없음·Column 없음·FK 없음 각각 `BusinessMetadataMappingError` 확인.
* 실제 Docker MSSQL 확인: `TASK-010`의 실제 Lifespan Startup이 `validate_physical_mapping()`을 통과해야 애플리케이션이 정상 기동하므로, 아래 `TASK-013`의 실제 DB 기반 테스트가 성공적으로 실행됐다는 사실 자체가 이 검증을 실제 Schema로 통과했음을 의미한다.

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-004` RuntimeIntent 생성과 Contract 검증

* Status: `Completed`
* 요구사항: `FR-003`
* 실제 변경 파일:
  * `app/services/intent_resolver.py`

구현 결과:

* `RuntimeIntent` Pydantic Model이 Contract의 7개 필드, `request_type`/`requested_output` Enum, `extra="forbid"`, `requires_clarification`↔`clarification_reason`↔`requested_concepts`↔`subject` 조건부 불변조건을 모두 구현한다. `generate_runtime_intent()`가 `llm_client.complete_json()`을 호출하고 `json.JSONDecodeError`·`pydantic.ValidationError` 모두 `IntentContractViolationError`로 변환한다. `LLMUnavailableError`는 그대로 전파한다(설정·호출 실패와 Contract 위반을 구분).
* System Prompt에 개념 어휘 고정 규칙을 추가했다: "재고 관련 질문은 `requested_concepts`에 반드시 '재고'를, 안전재고 관련 질문은 반드시 '안전재고'를 그대로 포함한다"(아래 "구현 중 발견 사항" 참고). 이 규칙이 없을 때는 실제 Gemini가 "미달", "창고별 수량 합계" 같은 동의어를 만들어 `metadata_retriever`의 Alias 매칭에 실패했다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_intent_resolver.py`
* 결과: 통과 (11 passed) — 정상 생성, 유효한 명확화, `LLMUnavailableError` 전파, Contract 위반 7종(잘못된 Enum, 추가 필드, 빈 `requested_concepts`, 조건 불일치 2종, 필수 필드 누락), `explicit_parameters` 중첩 객체 거부.
* 실제 Gemini 확인(수동): 대표 질문과 한국어 표현 3종 모두 `generate_runtime_intent()`로 Contract를 만족하는 결과를 받았고, 어휘 고정 규칙 추가 후 3종 모두 `requested_concepts: ["재고", "안전재고"]`로 수렴함을 확인했다.

Plan과의 차이:

* System Prompt에 개념 어휘 고정 규칙 문단을 추가했다. Plan은 Alias 목록 자체("inventory", "재고", "현재 재고" 등 5개 표현)를 확정했지만 Prompt 문구는 "Private Helper"로 남겼으므로, 실제 Gemini 응답이 그 Alias 안에 들어오도록 Prompt를 조정하는 것은 Plan이 정의한 Alias 집합이나 매칭 알고리즘(정확히 일치, Fuzzy 매칭 없음)을 바꾸지 않는 구현 세부사항이다.

Reviewer 의견과 처리:

* 미검토

## `TASK-005` Metadata 검색과 Metadata Context 구성

* Status: `Completed`
* 요구사항: `FR-005`
* 실제 변경 파일:
  * `app/services/metadata_retriever.py`
  * `app/services/context_builder.py`

구현 결과:

* `metadata_retriever.retrieve()`가 Plan이 정의한 Alias 집합(Entity `product`, Concept `inventory`/`safety_stock`)으로 `intent.subject`/`intent.requested_concepts`를 trim+소문자 정규화 후 정확히 일치 비교한다. 세 조건이 모두 만족해야 `metadata_service.all_entries()`(8개) 전체를 반환하고, 하나라도 없으면 `MetadataNotFoundError`.
* `context_builder.build()`가 kind별로 Entry를 묶어 `MetadataContext`(entities/dimensions/metrics/filters/grains/joins 6개 dict)를 만든다. `known_ids()`는 plan_validator가, `as_prompt_dict()`는 query_planner·sql_generator가 LLM Prompt 구성에 사용한다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_metadata_retriever.py`
* 결과: 통과 (6 passed) — 대표 질문·한국어 Alias·대소문자와 공백 정규화 성공 3건, 범위 밖 Subject·개념 절반만 일치·완전히 범위 밖 개념 실패 3건.
* `context_builder`는 별도 파일 없이 `test_query_planner.py`/`test_plan_validator.py`/`test_sql_guardrail.py`가 `context_builder.build(metadata_service.all_entries())`를 공통으로 사용해 간접 검증한다(모든 QueryPlan/SQL 테스트가 이 Context를 기준으로 통과·실패하므로 중복 테스트를 추가하지 않았다).

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-006` QueryPlan 생성과 검증

* Status: `Completed`
* 요구사항: `FR-006`
* 실제 변경 파일:
  * `app/services/query_planner.py`
  * `app/services/plan_validator.py`

구현 결과:

* `query_planner.QueryPlan`이 Contract의 11개 필드, `filters[]`/`order_by[]` 하위 Model, `extra="forbid"`, 중복 ID 금지, `metric_ids` 최소 1개, `order_by` 최소 1개와 `field_id`가 `dimension_ids`/`metric_ids` 안에 있어야 하는 규칙을 구현한다(구조적 검증). `QueryPlanInvalidError`를 이 파일에 정의해 구조 위반과 의미 위반이 같은 예외 타입을 공유하도록 했다(순환 Import 회피, `plan_validator.py`가 `from app.services.query_planner import QueryPlan, QueryPlanInvalidError`로 재사용·재노출).
* QueryPlan 생성 Prompt에 "Metadata Context의 filters 항목 description이 질문 조건과 일치하면 반드시 포함하라"는 규칙을 추가했다(아래 "구현 중 발견 사항" 참고).
* **`plan_validator.validate()`를 Codex 구현 검토(발견 1·2)를 반영해 다시 작성했다.** 두 단계로 검증한다: (1) 종류별 검증 — `entity_id`는 `context.entities`, `dimension_ids`는 `context.dimensions`, `metric_ids`는 `context.metrics`, `filters[].filter_id`는 `context.filters`, `grain_id`는 `context.grains`, `join_ids`는 `context.joins`에서만 찾는다(`context.known_ids()` 하나로 합쳐 검사하던 이전 방식은 제거했다 — 존재하기만 하면 종류가 달라도 통과하는 문제를 막는다). `time_policy_id`는 이 Demo Scope에 승인된 Time Policy가 없으므로 `null`만 허용한다. (2) FEAT-0004 고정 Demo Scope 필수 항목 — `entity_id == "product"`, `dimension_ids ⊇ {product_id, product_name}`, `metric_ids ⊇ {current_inventory, safety_stock_level}`, `filters`에 `below_safety_stock`이 반드시 있고 `parameters`가 비어 있음, `join_ids ⊇ {product_to_product_inventory}`, 기존 `grain_id == "product"`, `depth == 1`, 첫 정렬 `product_id asc`, `1<=limit<=100`. Registry가 각 kind마다 정확히 필요한 만큼만 등록되어 있으므로 이 두 단계가 결합되면 Demo Scope 밖의 추가 Dimension·Metric·Filter·Join도 자연히 거부된다(레지스트리에 그 kind로 등록된 다른 id가 없기 때문). 상수는 `_REQUIRED_ENTITY_ID`/`_REQUIRED_DIMENSION_IDS`/`_REQUIRED_METRIC_IDS`/`_REQUIRED_FILTER_ID`/`_REQUIRED_JOIN_IDS`/`_REQUIRED_GRAIN_ID`/`_REQUIRED_FIRST_ORDER_BY` 모듈 상수로 한 곳에만 정의해 중복 나열을 피했다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_query_planner.py tests/test_plan_validator.py`
* 결과: 통과 (28 passed — `test_query_planner.py` 9개 + `test_plan_validator.py` 19개) — 구조 위반 8종, 종류별 검증 6종(Entity/Dimension/Metric/Filter/Grain/Join 각각 잘못된 kind), 고정 Demo Scope 필수 항목 7종(빈 filters, filter parameters 비어있지 않음, 필수 Metric 2종 각각 누락, 필수 Join 누락, `time_policy_id` non-null, Demo Scope 밖 Dimension), 기존 항목(표시 Dimension 누락, 첫 정렬 오류, `limit` 상한 초과) 유지.
* 실제 Gemini 확인(수동, 필터 규칙 추가 전 1회, 이전 라운드): 대표 질문으로 `generate_query_plan()`+`validate()`가 성공했으나 **`filters`가 빈 배열로 생성됨을 발견**했다. 이 발견을 계기로 Prompt 수정에 더해 Codex 구현 검토에서 Backend 강제 검증(위 (1)(2))이 필요하다는 지적을 받아 이번 라운드에서 반영했다. Prompt·Backend 검증 모두 적용한 뒤의 실제 재확인은 Gemini 일일 할당량 소진으로 하지 못했다(`TASK-013`, 남은 위험 참고).

Plan과의 차이:

* `QueryPlanInvalidError`를 Plan 공개 경계 표기(`plan_validator.py`에만 나열)와 달리 `query_planner.py`에 정의하고 `plan_validator.py`가 재노출(`__all__`)한다. Plan이 `plan_validator.py`가 이미 `QueryPlan`을 `query_planner.py`에서 import하도록 설계했으므로, 예외를 반대 방향으로 import하면 순환 참조가 발생해 구조 위반과 의미 위반이 같은 예외 타입(`rejected/query_plan_invalid`)을 공유한다는 Plan의 의도를 지키면서 위치만 바꿨다. `from app.services.plan_validator import QueryPlanInvalidError`는 Plan 문서대로 계속 동작한다.
* QueryPlan 생성 Prompt에 filter 포함 규칙 문단을 추가했다(TASK-004와 같은 성격의 Private Helper 조정).
* `plan_validator.validate()`의 검증 범위를 Codex 구현 검토(발견 1·2)에 따라 확장했다. Plan은 "Metadata Context 참조 존재 여부, 고정 Demo Scope, FEAT-0004 전용 규칙(depth, grain_id, order_by[0], limit 상한)을 확인한다"는 일반 원칙만 정의했고 정확한 검증 항목·강도는 구현 세부사항으로 남겼으므로, 공개 함수 시그니처(`validate(plan, context) -> QueryPlan`)는 그대로 유지하며 그 원칙을 더 엄격하게 구현한 것으로 판단해 Plan을 수정하지 않고 진행했다.

Reviewer 의견과 처리:

* 미검토

## `TASK-007` SQL 생성과 Backend SQL Guardrail(12개 규칙)

* Status: `Completed`
* 요구사항: `FR-007`, `NFR-003`
* 실제 변경 파일:
  * `app/services/sql_generator.py`
  * `app/services/sql_guardrail.py`

구현 결과:

* `sql_generator.generate_sql()`은 항상 `llm_client.complete_text()`를 호출해 SQL을 생성하고 Markdown 코드 Fence를 벗겨낸다. 고정 SQL 매핑 코드 경로는 없다.
* `sql_guardrail.validate()`가 Approved Plan의 12개 규칙을 정확히 그 순서로 구현한다: (1)다중 Statement, (2)문자열 Literal 전면 거부(Fail Closed, 마스킹 없음), (3)주석, (4)`SELECT` 정확히 1회, (5)SELECT 시작+금지 키워드 17개, (6)`TOP` 필수+1~100 상한, (7)`*` 전면 거부, (8)Table Allowlist(`Product`/`ProductInventory`, Schema 접두사·대괄호 허용), (9)`AS` Table Alias 필수(암묵적 별칭 거부), (10)출력 Column Alias를 Table Alias보다 먼저 분류해 승인 4종(`ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel`)과 정확히 일치하는지 확인, (11)전체 식별자 Allowlist(예약어·Table·Schema 토큰·앞서 승인한 Table/출력 Alias·원본 Column 4종), (12)`ORDER BY` 존재+첫 정렬 키 `ProductID ASC`. 규칙 10을 규칙 11보다 먼저 실행해 `SUM(pi.Quantity) AS CurrentInventory` 같은 정상 Aggregate 표현의 출력 Alias가 전체 식별자 검사에서 거부되지 않도록 했다.
* **Codex 구현 검토(발견 3)를 반영해 규칙 12 뒤에 "FEAT-0004 고정 Demo Scope 최소 의미 검증" 절을 추가했다.** 기존 12개 규칙 번호는 그대로 두고 별도 절로 보강했다: 두 필수 Table(`Product`/`ProductInventory`)이 모두 참조되는지, `ON <alias>.ProductID = <alias>.ProductID` 형태로 두 Table Alias가 ProductID로 Join되는지, `SUM(...Quantity...) AS CurrentInventory`로 현재 재고가 집계되는지(HAVING 절의 SUM만으로는 인정하지 않고 출력 Alias에 직접 연결된 SUM만 인정), `HAVING SUM(...Quantity...) < ...SafetyStockLevel` 방향의 안전재고 부족 조건이 있는지, 4개 출력 Alias(`ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel`)가 모두 존재하는지를 정규식으로 확인한다. 공개 함수 시그니처 `validate(sql, context) -> str`는 바꾸지 않았고 SQL Parser를 도입하지 않았다.
* **이번 라운드에 Codex 재검토 발견(JOIN이 실제로 가리키는 Table을 확인하지 않는 문제)을 반영해 Table Alias 관리 방식을 바꿨다.** 기존에는 Table Alias를 단순 `set`으로만 관리해 "Alias 문자열이 등록되어 있는지"만 확인했다. 이 때문에 `Production.Product`를 `p`/`p2` 두 Alias로 중복 끌어와 `p2`를 `p.ProductID = p2.ProductID`로 Join해 정상 Product-ProductInventory Join처럼 보이게 하고, 정작 `ProductInventory`는 `p.ProductID = p.ProductID` 항등 조건으로만 붙이는 SQL이 규칙 8~12와 의미 검증 문자열 매칭을 모두 통과할 수 있었다(실질적으로 제약 없는 Cross Join). 이를 막기 위해 Table Alias를 `alias -> table` 매핑(`table_alias_to_table: dict[str, str]`)으로 바꿔 다음을 추가로 강제한다: (1) 같은 Alias의 중복 선언 거부, (2) **같은 Table의 중복 참조 자체를 거부**(다른 Alias로 같은 Table을 두 번 끌어오는 것 자체를 막아 위 우회의 근본 원인을 제거), (3) ProductID Join의 두 Alias가 실제로 `{Product, ProductInventory}` 집합을 가리키는지 확인(Alias 문자열이 아니라 매핑된 Table로 비교), (4) `SUM(...)`의 Quantity Alias가 반드시 `ProductInventory`를 가리키는지, HAVING의 SafetyStockLevel Alias가 반드시 `Product`를 가리키는지, SELECT 집계와 HAVING 집계가 같은 Inventory Alias를 쓰는지 확인. Alias 매칭은 SQL Server 기본 동작대로 대소문자를 구분하지 않는다(내부적으로 대문자로 정규화). 공개 함수 시그니처는 바꾸지 않았고 SQL Parser는 도입하지 않았다.
* `mcp_server/readonly_query_executor.py`의 SELECT-only·단일 Statement·금지 키워드 재검증은 손대지 않았다 — Backend와 MCP Server가 서로 다른 신뢰 경계에서 의도적으로 중복 검증한다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_sql_guardrail.py`
* 결과: 통과 (39 passed — 이번 라운드에 7개 추가) — 정상 Aggregate SQL(`SUM(pi.Quantity) AS CurrentInventory` 포함) 통과 회귀 테스트, Bracket 표기 허용, 세미콜론 정리, 구조 규칙 위반 19종, 고정 Demo Scope 의미 검증 위반 7종, 공백 SQL, 새 의미 검증 포함 정상 대표 SQL 재통과 확인, **JOIN Alias 위장 우회 6종 거부**(자기 Join으로 위장한 Product-ProductInventory Join, 진짜 Join 뒤에 매달린 항등 조건 ProductInventory 재참조, Quantity 집계에 Product Alias 사용, SafetyStockLevel에 ProductInventory Alias 사용, 중복 Table Alias 선언 2종) + **대소문자 다른 Alias가 스스로와는 정상 매칭됨** 확인(신규).
* 실제 Gemini 확인: 이번 라운드는 무료 할당량을 소비하지 않기 위해 실제 Gemini API를 호출하지 않았다(사용자 지침). 이전 라운드의 수동 확인(대표 질문 SQL이 이전 12개 규칙 통과, `filters` 누락으로 `HAVING` 없었음)에서 더 진행하지 않았다.

Plan과의 차이:

* 기존 12개 구조 규칙 자체는 변경 없음(9개→12개로의 확장은 이전 Codex 재검토에서 이미 Plan에 반영된 상태였다). "FEAT-0004 고정 Demo Scope 최소 의미 검증"(이전 라운드 추가)과 이번 라운드의 Alias `alias -> table` 매핑 강화는 모두 Plan이 "SQL은 MCP 호출 전 Backend 자체 최소 검증을 통과해야 한다"고 정의한 원칙 안에서 QueryPlan이 강제하는 안전재고 Filter와 승인된 Join이 실제 SQL 문자열에도 정확히 반영되도록 보강한 것이며, 공개 시그니처·기존 12개 규칙 번호·정규식·토큰 기반 접근 방식은 바꾸지 않았다. SQL Parser나 FEAT-0006의 범용 Plan-SQL Match는 도입하지 않았다.

Reviewer 의견과 처리:

* 미검토

## `TASK-008` Workflow Orchestrator(`agent_service.py`)

* Status: `Completed`
* 요구사항: `FR-001`, `FR-008`, `FR-009`, `NFR-004`
* 실제 변경 파일:
  * `app/services/agent_service.py`

구현 결과:

* `CompletedOutcome`/`ClarificationRequiredOutcome`/`RejectedOutcome`/`FailedOutcome` 4개 Model(`status` Discriminator)로 `QuestionOutcome`을 정의했다. `RejectedOutcome.code`/`FailedOutcome.code`는 Contract가 정의한 값만 갖는 `Literal`이고 4개 Model 모두 `extra="forbid"`이며 `message`는 공통 `field_validator`로 비어있지 않음을 강제한다.
* `handle_question()`이 RuntimeIntent → (명확화 조기 반환) → Metadata 검색 → Context 구성 → QueryPlan 생성·검증 → SQL 생성·Guardrail → `mcp_client_manager.execute_readonly_query(parameters=[], query_timeout_seconds=10, maximum_returned_rows=100)` 순서로 호출한다. 각 단계 예외를 Plan이 정의한 매핑대로 변환하고, 분류되지 않은 예외는 내부 Wrapper(`_handle_question`)를 감싼 바깥쪽 `try/except Exception`이 `failed/internal_error`로 변환해 절대 예외를 상위로 전파하지 않는다.
* **이번 라운드에 Codex 재검토 발견(Rate Limit을 사용자가 구분하지 못하는 문제)을 반영해 `_llm_unavailable_message(exc)` Helper를 추가했다.** 공개 `code`는 3곳의 `except LLMUnavailableError` 분기 모두 계속 `"llm_unavailable"`로 고정하되, `exc.reason == "rate_limited"`일 때만 `message`를 재시도를 안내하는 별도 문자열("LLM 사용 한도를 초과했거나 일시적으로 요청이 제한되었습니다. 잠시 후 다시 시도해 주세요.")로 바꾸고, 그 외 모든 `reason`(`configuration_error`/`timeout`/`provider_error`/`empty_response`)은 기존 일반 메시지("설정된 LLM Provider를 사용할 수 없습니다.")를 그대로 유지한다. Provider 원문 오류, API Key, 응답 Body, Stack Trace는 어느 경우에도 `message`에 포함하지 않는다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_agent_service.py`
* 결과: 통과 (20 passed — 이번 라운드에 2개 추가) — 대표 질문·한국어 표현 3종 성공(Fake), 명확화 시 MCP 미호출, 9개 실패 분기(`llm_unavailable`, `intent_contract_violation`, `metadata_not_found`, `query_plan_invalid` 구조/의미/필수 Filter 누락 3종, `sql_rejected`, `mcp_execution_failed` 2종, `internal_error`), Discriminated Union의 추가 필드·잘못된 `code`·빈 `message` 거부, `CompletedOutcome`에 `code`/`message` 필드 자체가 없음 확인, 필수 Filter가 빠진 QueryPlan이 SQL 생성·MCP 호출 전에 거부됨(Codex 발견 1) 확인, **`reason="rate_limited"`일 때 공개 `code`는 `llm_unavailable`을 유지하면서 재시도 안내 메시지를 반환하고 원문(Secret Marker)이 노출되지 않음**(신규), **그 외 `reason`(`provider_error`)은 기존 일반 메시지를 유지하고 원문이 노출되지 않음**(신규) 확인.

Plan과의 차이:

* `handle_question()`의 `except LLMUnavailableError` 3곳이 `_llm_unavailable_message(exc)`를 통해 `reason`에 따라 다른 `message`를 반환하도록 바뀌었다. 공개 Contract의 `code`(`llm_unavailable` 하나로 고정)와 예외 → `code` 매핑 자체는 바뀌지 않았고, Plan은 "원본 LLM 오류를 노출하지 않는 고정 메시지로 표현한다"는 원칙만 정의했으므로 `message` 문구를 내부 `reason`에 따라 세분화한 것은 그 원칙 안의 조정으로 판단해 Plan을 수정하지 않고 진행했다.

Reviewer 의견과 처리:

* 미검토

## `TASK-009` 자연어 질문 API와 `/api/questions` 전용 Validation Handler

* Status: `Completed`
* 요구사항: `FR-001`, `NFR-004`
* 실제 변경 파일:
  * `app/api/query.py`
  * `main.py`

구현 결과:

* `QuestionRequest(extra="forbid")`+`field_validator`로 빈 질문을 거부한다. `POST /api/questions`가 `Depends`로 `app.state`의 `llm_client`/`mcp_client_manager`/`physical_metadata_catalog`를 받아 `agent_service.handle_question()`을 호출하고 `status`→HTTP 상태 코드(`completed`/`clarification_required`→200, `rejected`→422, `failed`→500)로 응답한다.
* `validation_exception_handler`가 `request.url.path == "/api/questions"`인 경우만 새 Correlation ID로 `rejected/invalid_request` Contract 응답을 만들고, 그 외 경로는 `fastapi.exception_handlers.request_validation_exception_handler`(별칭 `default_request_validation_exception_handler`로 import)로 위임한다. `main.py`가 `app.add_exception_handler(RequestValidationError, query.validation_exception_handler)`로 전역 등록한다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q tests/test_api_query.py`
* 결과: 통과 (9 passed) — 추가 필드·빈 질문·필드 누락·비문자열·비Object Body·malformed JSON 모두 Correlation ID 포함 `rejected/invalid_request`(422) 확인, `/api/questions` 밖의 임의 경로(테스트 전용 `/other`)는 FastAPI 기본 `detail` 형식을 그대로 유지함을 확인, `FakeLLMClient`를 `dependency_overrides`로 주입한 실제 HTTP 왕복 성공 경로(`status=completed`) 확인.

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-010` FastAPI Lifespan 통합

* Status: `Completed`
* 요구사항: `FR-004`, `NFR-005`
* 실제 변경 파일:
  * `app/core/lifespan.py`

구현 결과:

* Admin DB 준비 → `OpenAICompatibleLLMClient()` 생성(검증 없음, `app.state.llm_client` 저장) → 기존 MCP Lifecycle 진입 → `inspect_schema` → `build_physical_metadata_catalog()` → `metadata_service.validate_physical_mapping()`(실패 시 그대로 전파) → `app.state.mcp_client_manager`/`physical_metadata_catalog` 저장 → `yield` 순서로 확장했다. 종료 시 `try: await llm_client.aclose() finally: engine.dispose()`로 `aclose()`가 실패해도 Admin DB Engine 정리가 항상 실행되도록 중첩했다.

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q -m "not requires_llm"`
* 결과: 통과 (이전 라운드 272 passed, 이번 라운드는 3건 추가 검증 - 아래 "최종 검증 기록" 참고) — 기존 FEAT-0001~0003 테스트(`test_health.py`, `test_app_lifecycle.py`, `test_admin_db_lifecycle.py`, MCP 전체) 전부 확장된 Fake Catalog로 회귀 없이 통과. LLM 환경변수를 설정하지 않은 상태(Fake 기반 테스트는 `app.state.llm_client`를 건드리지 않음)에서도 Startup이 막히지 않음을 확인.
* 실행 명령: `uv run pytest -q -m requires_target_db`(이전 라운드, Docker 기동 상태)
* 결과: 통과 (10 passed, 3 skipped — `requires_llm`도 겹치는 E2E 3건은 `RUN_LLM_TESTS` 없이 자동 Skip) — 실제 Docker MSSQL로 `validate_physical_mapping()`이 통과해야 Startup이 성공하므로, 이 10건이 통과했다는 사실 자체가 실제 Schema로 이 검증이 통과함을 의미한다. **이번 라운드는 이 Feature와 무관한 로컬 환경 사유로 Docker Desktop이 기동되어 있지 않아 이 10건을 재실행하지 못했다** — `plan_validator.py`/`sql_guardrail.py`/`llm_client.py`/`agent_service.py` 변경이 이 10건의 실제 DB 상호작용 자체에 영향을 주지 않으므로(모두 SQL 문자열·Python 예외 처리 로직 변경이며 `execute_readonly_query` 호출 방식은 그대로) 회귀 위험은 낮다고 판단하지만, 다음 세션에서 Docker를 기동해 재확인해야 한다(아래 "실행하지 못한 검증과 남은 위험" 참고).

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-011` 의존성과 테스트 인프라

* Status: `Completed`
* 요구사항: 구현 인프라(직접 대응하는 FR/NFR 없음)
* 실제 변경 파일:
  * `pyproject.toml`
  * `uv.lock`
  * `tests/conftest.py`

구현 결과:

* `pyproject.toml`에 `openai>=2.8,<3` 의존성과 `requires_llm` pytest marker를 추가했다. `uv lock`+`uv sync`로 `openai==2.47.0`(+`distro`/`jiter`/`sniffio`/`tqdm` 전이 의존성)을 설치했다.
* `tests/conftest.py`의 `FAKE_INSPECT_SCHEMA_RESULT`를 확장해 `Production.Product`에 `SafetyStockLevel`을, `Production.ProductInventory`(`ProductID`/`LocationID`/`Quantity`, 복합 PK)를 추가하고 둘 사이 Physical FK(`FK_ProductInventory_Product`)를 추가했다 — FEAT-0004의 최소 물리 매핑과 정확히 일치시켰다.
* `LLMClient` Protocol을 구현하는 `FakeLLMClient`(JSON/텍스트 응답 Queue, 호출 기록, 오류 주입 모드)를 추가했다. `FakeMCPClientManager`에 `execute_error` 생성자 인자를 추가해 MCP 실행 실패 경로를 시뮬레이션할 수 있게 했다(기존 사용에는 영향 없음, 기본값 `None`).
* `pytest_collection_modifyitems` Hook을 추가해 `os.environ.get("RUN_LLM_TESTS") == "1"`이고 `llm_client.is_configured()`가 `True`일 때만 `requires_llm` 테스트를 실행하고, 그 외에는 설정값을 포함하지 않는 고정 Reason으로 Skip한다. 모든 async 테스트가 공유하는 `anyio_backend`(`"asyncio"`) Fixture를 추가했다(기존 MCP 테스트 파일들은 자체 Fixture를 그대로 유지, 이 Feature의 신규 테스트만 공유 Fixture를 사용).

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q` (전체, `RUN_LLM_TESTS` 미설정, 이전 라운드)
* 결과: 통과 (293 passed, 3 skipped) — `requires_llm` 3건이 정확히 Skip됨을 확인.
* 실행 명령: `RUN_LLM_TESTS=1 uv run pytest -q -m "requires_target_db and requires_llm"`(이전 라운드)
* 결과: 실행됨(Skip되지 않음, 이후 결과는 `TASK-013` 참고) — Hook이 실제로 조건에 따라 실행/Skip을 전환함을 확인.
* 이번 라운드는 Fixture·Hook 자체를 수정하지 않았으므로 별도 재검증 없이 그대로 재사용했다. `tests/test_sql_guardrail.py`/`tests/test_llm_client.py`/`tests/test_agent_service.py`의 신규 테스트도 이 Hook·Fixture(특히 `FakeLLMClient`)를 그대로 사용해 통과함을 확인했다(위 각 TASK 참고).

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-012` FEAT-0004 신규 자동 테스트 스위트

* Status: `Completed`
* 요구사항: 7절/8절 테스트 전략 전체
* 실제 변경 파일:
  * `tests/test_metadata_service.py`(5개)
  * `tests/test_llm_client.py`(15개 — 이번 라운드에 3개 추가, Rate Limit/빈 응답/기본 reason)
  * `tests/test_intent_resolver.py`(11개)
  * `tests/test_metadata_retriever.py`(6개)
  * `tests/test_query_planner.py`(9개)
  * `tests/test_plan_validator.py`(19개 — 이전 라운드에 12개 추가, Codex 발견 1·2)
  * `tests/test_sql_guardrail.py`(39개 — 이전 라운드 8개 + 이번 라운드 7개 추가, JOIN Alias 위장 우회 거부)
  * `tests/test_agent_service.py`(20개 — 이전 라운드 1개 + 이번 라운드 2개 추가, Rate Limit 메시지)
  * `tests/test_api_query.py`(9개)

테스트 또는 검증 결과:

* 실행 명령: `uv run pytest -q -m "not requires_llm and not requires_target_db"`(이번 라운드는 로컬 Docker Desktop이 기동되어 있지 않아 Docker 필요 10건도 함께 제외하고 실행했다)
* 결과: 통과 (295 passed, 13 deselected) — 전체 스위트는 308개(기존 172개 + FEAT-0004 신규 136개, 이 중 `requires_llm` 3건과 `requires_target_db` 10건 합쳐 13건 제외). 아래 "최종 검증 기록"에 전체 목록.

Plan과의 차이:

* 없음.

Reviewer 의견과 처리:

* 미검토

## `TASK-013` 실제 Gemini E2E와 Golden Query 검증

* Status: `Completed`
* 요구사항: `FR-010`
* 실제 변경 파일:
  * `tests/test_e2e_golden_query.py`(3개, `requires_target_db`+`requires_llm`)

구현 결과:

* Golden SQL(`Production.Product`↔`Production.ProductInventory` INNER JOIN, `HAVING SUM(Quantity) < SafetyStockLevel`, `ORDER BY ProductID`)을 테스트 코드에 고정하되 그 결과는 `mcp_lifespan()`으로 얻은 실제 `MCPClientManager.execute_readonly_query()`로 매 테스트 실행마다 새로 조회한다(`pyodbc` 직접 연결 없음). 대표 질문과 한국어 표현 3종을 실제 `OpenAICompatibleLLMClient()`+실제 `mcp_lifespan()`으로 `agent_service.handle_question()`을 호출한다.
* **이번 라운드에 Codex 구현 검토 발견 4를 반영해 비교 로직을 강화했다.** 기존에는 `ProductID`/`CurrentInventory`/`SafetyStockLevel` 3개 필드만 비교했으나, `Name`을 포함한 4개 필드(`ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel`)를 모두 비교하도록 수정했다. `_extract_comparable_rows(columns, rows)` Helper가 Golden 결과와 Pipeline 결과 양쪽에서 컬럼 위치를 이름으로 찾아 4개 필드 Tuple 목록으로 정규화하고, 필요한 컬럼이 없으면 `assert`가 어떤 컬럼이 없는지 명시하며 즉시 실패한다. `ProductID` 오름차순이 유지된 전체 목록을 비교하며, 생성 SQL 문자열 자체는 비교하지 않는다.

테스트 또는 검증 결과:

**이전 라운드까지의 경과**(요약, 상세는 이전 tasks.md 이력과 동일): (1) Token 상한 원래 값(500/800/600)에서 RuntimeIntent JSON이 `finish_reason: "length"`로 잘리고 Gemini가 표준 Alias 밖 동의어를 생성해 실패 → Token 상한과 RuntimeIntent Prompt 수정. (2) 대표 질문 1건 수동 확인에서 QueryPlan의 `filters`가 빈 배열로 생성되는 문제 발견 → QueryPlan Prompt에 filter 포함 규칙 추가. (3) 이 수정 직후 Gemini 무료 등급 일일 할당량(20회/일, `gemini-3.6-flash`)을 소진해 재확인 실패.

**2차 라운드(Codex 1차 검토 대응)**: Codex 구현 검토에서 "Prompt 지시만으로는 LLM 산출물을 신뢰할 수 없다"는 지적에 따라 `plan_validator.py`(발견 1·2)와 `sql_guardrail.py`(발견 3)에 Backend 강제 검증을 추가했다(Fake 기반 회귀 테스트로 이 강제 검증 자체는 확인 완료 — 아래 "Codex 구현 검토 발견 사항과 수정(1차)" 참고). 이 강화된 Backend 검증이 실제 Gemini 응답에도 올바르게 동작하는지, 그리고 Golden Query와 4개 필드가 실제로 일치하는지 최종 확인하기 위해 `RUN_LLM_TESTS=1`로 **정확히 한 번** 재실행했다.

* 실행 명령: `RUN_LLM_TESTS=1 uv run pytest -q -m "requires_target_db and requires_llm"`
* 실행 시각: 2026-07-23 22:28(KST)
* 결과: **3 failed**(전부 `status=failed, code=llm_unavailable`) — 원인은 Gemini 무료 등급의 일일 요청 한도가 이전 세션에서 소진된 이후 2차 라운드 작업 시점까지도 회복되지 않았기 때문이다(`openai.RateLimitError` → `LLMUnavailableError`로 원문 노출 없이 올바르게 변환되는 것은 확인했지만, 목표였던 Golden Query 비교는 그때도 수행하지 못했다). 이 실패를 통과로 표현하지 않았으며, 지침에 따라 할당량을 더 소비하는 재시도를 하지 않았다.
* `RUN_LLM_TESTS` 미설정 시: `uv run pytest -q tests/test_e2e_golden_query.py` → 3 skipped(정상 — Hook이 의도대로 동작함을 2차 라운드에도 재확인).

**3차 라운드(Codex 2차 재검토 대응, 이번 라운드)**: 사용자 지침에 따라 **이번 라운드는 실제 Gemini API를 전혀 호출하지 않았다** — 무료 할당량을 소비하지 않기 위해 Fake 기반 테스트만 실행했다. 따라서 `TASK-013`은 이번에도 실제 통과 여부를 확인하지 못한 채 `Needs Fix` 상태를 유지한다. `RUN_LLM_TESTS` 미설정 상태에서 `uv run pytest -q tests/test_e2e_golden_query.py`가 3건 모두 Skip되는 것만 재확인했다(Hook·Fixture를 이번 라운드에 손대지 않았으므로 동작 변화 없음).

**최종 실제 Gemini E2E 검증(2026-07-24 KST)**:

* 실제 실행 조건: Windows 가상환경 프로세스 안에서 `RUN_LLM_TESTS=1`을 설정하고 `tests/test_e2e_golden_query.py` 실행. 실제 Gemini Provider와 Docker MSSQL MCP를 모두 사용했다.
* 첫 실제 실행 결과: `1 passed, 2 failed`. 대표 질문은 Golden Query와 일치해 통과했고, 나머지 두 표현 변형은 공개 `code=llm_unavailable`과 Rate Limit 전용 안전 메시지로 실패했다. 원문 Provider 오류나 Secret은 노출되지 않았다.
* 재실행 명령: `.venv/Scripts/python.exe -c "import os, pytest; os.environ['RUN_LLM_TESTS']='1'; raise SystemExit(pytest.main(['-q', 'tests/test_e2e_golden_query.py']))"`
* 재실행 결과: **3 passed in 17.24s**. 대표 질문과 한국어 표현 변형 세 건 모두 `completed`였고, 실제 MCP 조회 결과가 Golden Query의 `ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel` 전체 행·순서와 일치했다.
* 판정: 일시적인 Rate Limit은 재시도로 회복됐고 `FR-010`의 실제 End-to-End 완료 조건을 충족했다.

Plan과의 차이:

* 없음. 테스트 설계와 실행 전환이 Plan대로 동작하고, 최종 실제 Gemini 실행에서 세 질문이 Golden Query의 4개 필드 전체 결과와 일치함을 확인했다.

Reviewer 의견과 처리:

* Codex 최종 검증 완료 — 실제 Gemini E2E 3건 통과 확인

## 구현 중 발견 사항

### Gemini의 숨겨진 reasoning Token이 `max_completion_tokens` 예산을 소비함

Plan이 정한 Token 상한(RuntimeIntent 500, QueryPlan 800, SQL 600)으로 실제 `gemini-3.6-flash`를 호출하면 `finish_reason: "length"`로 응답이 중간에 잘렸다. `usage.completion_tokens`(가시 출력)는 20 정도인데 `usage.total_tokens`(가시+비가시 총합)는 861까지 올라가는 것을 확인해, 응답에 보이지 않는 reasoning Token이 예산 대부분을 먼저 소비한다는 것을 확인했다. 2000/3000/2000으로 올린 뒤 `finish_reason: "stop"`으로 정상 종료되고 JSON이 완전한 형태로 반환됨을 확인했다. Gemini 전용 분기나 SDK를 추가하지 않고 일반적인 `max_completion_tokens` 값 조정만으로 해결했다.

### QueryPlan `filters`가 빈 배열로 생성되어 안전재고 조건이 SQL에서 누락될 위험

Plan은 QueryPlan Contract 구조와 `filters[].filter_id`가 Metadata Context 안에 있어야 한다는 규칙은 검증하지만, "질문 의도에 맞는 filter를 반드시 포함해야 한다"는 규칙은 Prompt(Private Helper) 영역이었다. 실제 Gemini가 대표 질문에도 `filters: []`를 반환한 사례를 발견했고, 이 경우 Backend SQL Guardrail은 구조적 규칙만 검사하므로 안전재고 조건이 없는 SQL도 통과시킬 수 있었다. Prompt에 "질문 조건과 일치하는 Metadata Context의 filter를 빠뜨리지 말라"는 명시적 규칙을 추가해 대응했다. **이 수정은 Gemini 일일 할당량 소진으로 실제 재확인을 완료하지 못했다** — Codex 검토와 별개로, 이 Feature를 완전히 완료로 보고하려면 할당량이 회복된 뒤(또는 더 높은 등급/다른 시간대) `RUN_LLM_TESTS=1 uv run pytest -q -m "requires_target_db and requires_llm"`로 3건이 모두 통과하는지 다시 확인해야 한다.

## Codex 구현 검토 발견 사항과 수정(1차)

Codex가 구현을 검토해 발견한 5건이다. 3차 재검토 결과 발견 1·2·4·5는 수정 내용을 확인해 `Resolved`로 변경했고, 발견 3은 필수 HAVING 문자열 뒤에 `OR 1 = 1`을 붙이는 새 우회가 재현되어 `Needs Fix`로 다시 열었다.

### 발견 1 — 고정 Demo Scope의 필수 QueryPlan 의미가 강제되지 않음(High)

* 실제 수정 파일: `app/services/plan_validator.py`
* 추가한 회귀 테스트: `tests/test_plan_validator.py`에 7개 추가(`test_validate_rejects_empty_filters`, `test_validate_rejects_missing_below_safety_stock_filter`, `test_validate_rejects_missing_required_metric`×2, `test_validate_rejects_missing_required_join`, `test_validate_rejects_non_null_time_policy_id`, `test_validate_rejects_dimension_id_outside_demo_scope`). `tests/test_agent_service.py`에 1개 추가(`test_query_plan_missing_required_filter_rejected_before_sql_and_mcp`) — 필수 Filter가 빠진 QueryPlan이 Agent 흐름에 들어오면 `sql_generator`(LLM 호출)와 MCP가 전혀 호출되지 않음을 확인.
* 실제 테스트 결과: `uv run pytest -q tests/test_plan_validator.py tests/test_agent_service.py` → 통과 (37 passed: 19 + 18).
* Plan과의 차이: 없음(공개 시그니처 `validate(plan, context) -> QueryPlan` 불변). Plan이 "Metadata Context 참조 존재 여부, 고정 Demo Scope, FEAT-0004 전용 규칙"을 검증한다는 일반 원칙만 정의하고 정확한 항목·강도는 구현 세부사항으로 남긴 범위 안에서, 실제로 필수 항목을 강제하도록 구현을 보강했다.
* 현재 상태: `Resolved`(Codex 3차 재검토에서 종류별 필수 항목 검증과 관련 회귀 테스트 확인)

### 발견 2 — Metadata ID의 종류별 검증이 없음(High)

* 실제 수정 파일: `app/services/plan_validator.py`(발견 1과 같은 파일, 같은 수정)
* 추가한 회귀 테스트: `tests/test_plan_validator.py`에 6개 추가(`test_validate_rejects_metric_id_used_as_entity_id`, `test_validate_rejects_join_id_used_as_dimension_id`, `test_validate_rejects_filter_id_used_as_metric_id`, `test_validate_rejects_metric_id_used_as_join_id`, `test_validate_rejects_metric_id_used_as_filter_id`, `test_validate_rejects_grain_id_of_wrong_kind` — 기존 `test_validate_rejects_grain_other_than_product`를 이 검증에 맞게 이름·Assertion을 갱신).
* 실제 테스트 결과: 위 발견 1과 같은 실행(같은 파일).
* Plan과의 차이: 없음. `context.known_ids()`로 전체를 합쳐 검사하던 기존 방식을 제거하고 `entities`/`dimensions`/`metrics`/`filters`/`grains`/`joins` 6개 그룹 각각에서 검사하도록 정밀도만 높였다.
* 현재 상태: `Resolved`(Codex 3차 재검토에서 Metadata ID 종류별 검증과 관련 회귀 테스트 확인)

### 발견 3 — QueryPlan Filter가 있어도 생성 SQL에서 조건이 누락될 수 있음(High)

* 실제 수정 파일: `app/services/sql_guardrail.py`
* 추가한 회귀 테스트: `tests/test_sql_guardrail.py`에 8개 추가 — `test_demo_scope_semantic_checks_reject_incomplete_sql`(Parametrize 7종: `missing_having_clause`, `having_direction_reversed`, `current_inventory_not_computed_with_sum`, `missing_required_join`, `missing_required_table_productinventory`, `missing_current_inventory_output_alias`, `missing_safety_stock_level_output_alias`) + `test_representative_sql_still_passes_after_demo_scope_semantic_checks`(정상 대표 SQL 재통과 확인).
* 실제 테스트 결과: `uv run pytest -q tests/test_sql_guardrail.py` → 통과 (32 passed).
* Plan과의 차이: 없음(공개 시그니처 `validate(sql, context) -> str` 불변, 기존 12개 규칙 번호 유지, 정규식·토큰 기반 유지, SQL Parser 미도입). 기존 12개 규칙 뒤에 고정 Demo Scope 전용 의미 검증 절을 추가하는 형태로 보강했다.
* 현재 상태: `Resolved`(발견 D의 Clause 완전 일치 비교와 직접 공격 거부를 Codex 4차 재검토에서 확인)

### 발견 4 — Golden Query E2E에서 제품명을 비교하지 않음(Medium)

* 실제 수정 파일: `tests/test_e2e_golden_query.py`
* 추가한 회귀 테스트: 신규 테스트 함수를 추가하지 않고 기존 3개(Parametrize) 테스트의 비교 로직 자체를 강화했다. `_extract_comparable_rows(columns, rows)` Helper를 추가해 Golden·Pipeline 양쪽 결과에서 `ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel` 4개 컬럼을 이름으로 찾아 Tuple 목록으로 정규화하고 전체 목록을 비교한다. 필요한 컬럼이 없으면 어떤 컬럼이 없는지 명시하며 즉시 실패한다.
* 실제 테스트 결과: 당시 `RUN_LLM_TESTS` 없이 실행한 결과는 3 skipped였고, 최종 실제 Gemini E2E에서는 4개 필드 전체 비교 3건이 모두 통과했다(`TASK-013` 참고).
* Plan과의 차이: 없음(테스트 코드 정밀도 개선, 공개 경계·Contract 영향 없음).
* 현재 상태: `Resolved`(비교 로직과 실제 Gemini E2E 3건의 4개 필드 전체 일치 확인)

### 발견 5 — Token 상한의 Plan 차이 기록이 부정확함(Medium)

* 실제 수정 파일: `docs/features/0004-natural-language-query-walking-skeleton/tasks.md`(`TASK-002`의 "Plan과의 차이" 문단만 수정, 코드 변경 없음)
* 추가한 회귀 테스트: 없음(문서 정확성 수정이며 동작 변경이 아니다).
* 실제 테스트 결과: 해당 없음.
* Plan과의 차이(수정된 설명 그 자체): Approved Plan은 RuntimeIntent 500·QueryPlan 800·SQL 600을 명시적으로 확정했었다. 실제 구현은 Gemini의 숨겨진 reasoning Token으로 인한 응답 절단을 관찰해 2000/3000/2000으로 조정한 **Plan과 다른 구현 세부사항**이다(이전 tasks.md의 "Plan이 정확한 수치를 고정하지 않았다"는 설명은 부정확했다). 공개 Contract·DB 접근 경계·보안 경계는 바꾸지 않았고, 호출당 Token 예산 증가로 비용·지연이 늘어날 수 있다. 이 수정에서 Approved `plan.md` 자체는 덮어쓰거나 수정하지 않았다.
* 현재 상태: `Resolved`(설명 정정과 Plan 본문 동기화를 확인)

## Codex 구현 재검토 발견 사항과 수정(2차)

Codex가 1차 수정 결과를 재검토해 발견한 3건이다. 3차 재검토 결과 발견 A·C의 코드 수정은 `Resolved`로 확인했고, 발견 B의 Plan 동기화도 내용상 타당함을 확인했다(Plan 상태 변경은 사용자 재승인 대기). 이번 라운드는 사용자 지침에 따라 실제 Gemini API를 호출하지 않고 Fake 기반 테스트만 실행했다.

### 발견 A — 잘못된 JOIN이 SQL Guardrail을 우회하는 문제(High)

* 실제 수정 파일: `app/services/sql_guardrail.py`
* 발견 내용: 이전 라운드에서 추가한 "FEAT-0004 고정 Demo Scope 최소 의미 검증"이 `ON a.ProductID = b.ProductID`의 두 Alias가 서로 다르고 등록된 Alias인지만 확인하고, 그 Alias가 실제로 어떤 Table을 가리키는지는 확인하지 않았다. 이 때문에 `Production.Product`를 `p`(정상)와 `p2`(위장) 두 Alias로 중복 참조해 `p2`를 진짜 `ProductInventory`인 것처럼 Join하고, 정작 `ProductInventory`는 `p.ProductID = p.ProductID` 항등 조건으로만 붙이는 SQL이 규칙 8~12와 의미 검증을 모두 통과할 수 있었다 — 결과적으로 제약 없는 Cross Join과 다를 바 없는 SQL이 승인될 위험이 있었다.
* 실제 수정 내용: Table Alias 관리를 단순 `set()`에서 `alias -> table` 매핑(`table_alias_to_table: dict[str, str]`)으로 바꾸고 다음을 추가로 강제했다: (1) 같은 Alias의 중복 선언 거부, (2) 같은 Table의 중복 참조 자체를 거부(우회의 근본 원인 제거), (3) ProductID Join의 두 Alias가 실제로 `{Product, ProductInventory}`를 가리키는지 매핑으로 확인, (4) `SUM(...)`의 Quantity Alias가 반드시 `ProductInventory`를, HAVING의 SafetyStockLevel Alias가 반드시 `Product`를 가리키는지, SELECT와 HAVING의 Inventory 집계가 같은 Alias를 쓰는지 확인. Alias 비교는 SQL Server 기본 동작대로 대소문자를 구분하지 않는다. 공개 함수 시그니처 `validate(sql, context) -> str`는 바꾸지 않았고 SQL Parser는 도입하지 않았다.
* 추가한 회귀 테스트: `tests/test_sql_guardrail.py`에 7개 추가 — `test_join_alias_impersonation_is_rejected`(Parametrize 6종: 자기 Join으로 위장한 Product-ProductInventory Join, 진짜 Join 뒤에 매달린 항등 조건 ProductInventory 재참조, Quantity 집계에 Product Alias 사용, SafetyStockLevel에 ProductInventory Alias 사용, 중복 Table Alias 선언 2종[대소문자 다른 경우 포함]) + `test_mixed_case_table_alias_still_matches_itself`(대소문자만 다른 정상 Alias는 계속 통과).
* 실제 테스트 결과: `uv run pytest -q tests/test_sql_guardrail.py` → 통과 (39 passed, 이전 32개 + 신규 7개). 기존 정상 대표 SQL 회귀 테스트도 함께 재확인해 통과했다.
* Plan과의 차이: 없음(공개 시그니처 불변, 기존 12개 규칙 번호·정규식/토큰 기반 접근 유지, SQL Parser 미도입). Plan이 정의한 "SQL은 MCP 호출 전 Backend 자체 최소 검증을 통과해야 한다"는 원칙을 더 정확하게 구현했다.
* 현재 상태: `Resolved`(Alias가 가리키는 실제 Table 검증과 중복 Table·Alias 거부를 확인. 별도의 Predicate `OR` 우회는 새 발견 D로 추적)

### 발견 B — Approved Plan과 Token 상한 불일치(Medium)

* 실제 수정 파일: `docs/features/0004-natural-language-query-walking-skeleton/plan.md`
* 발견 내용: 이전 라운드(발견 5)는 tasks.md의 "Plan과의 차이" 설명만 정정했을 뿐, Approved Plan 본문의 확정값(RuntimeIntent 500/QueryPlan 800/SQL 600)은 여전히 실제 구현값(2000/3000/2000)과 어긋난 채로 남아 있었다.
* 실제 수정 내용: `plan.md`의 "기술적 접근" 절 확정값을 실제 구현값(2000/3000/2000)으로 동기화하고, 변경 근거(숨겨진 reasoning Token으로 인한 응답 절단 관찰, 완전한 응답 확인, 비용·지연 증가 가능성)를 Plan 본문에 직접 기록했다. 검토 기록에 새 행을 추가했다. Approved Plan의 확정값을 바꾸는 변경이므로 이 Plan을 임의로 다시 `Approved` 처리하지 않고 `Status`를 `Draft`(Codex 재검토 대기)로 되돌렸다. Plan 승인 조건 체크리스트의 "필수 Codex 검토 의견이 해결되거나 기각 근거가 기록됨" 항목도 미충족으로 되돌렸다.
* 추가한 회귀 테스트: 없음(문서 동기화이며 코드 동작 변경이 아니다).
* 실제 테스트 결과: 해당 없음.
* Plan과의 차이: 이 발견 자체가 "Plan과 구현의 차이"를 다루므로, 수정은 차이를 없애는 방향(Plan을 구현에 맞춤)이었다. 코드의 Token 상한 값(2000/3000/2000)은 되돌리지 않았다(실제 Gemini 호환성을 위한 근거가 있는 값이므로 사용자 지침대로 유지). 공개 Contract, DB 접근 경계, 보안 경계는 변경하지 않았다.
* 현재 상태: Codex 재검토 완료, 사용자 Plan 재승인 대기(Token 상한 동기화와 근거는 구현·관찰 기록과 일치)

### 발견 C — LLM 할당량 초과를 사용자가 구별하지 못하는 문제(Medium)

* 실제 수정 파일: `app/services/llm_client.py`, `app/services/agent_service.py`
* 발견 내용: 설정 오류, Timeout, Rate Limit, 일반 Provider 오류, 빈 응답이 모두 `LLMUnavailableError` 하나로 뭉뚱그려져 `failed/llm_unavailable`로만 나타났다. 사용자 입장에서 "지금 재시도하면 될 문제"(Rate Limit)와 "설정을 고쳐야 하는 문제"를 구분할 수 없었다.
* 실제 수정 내용: 공개 Contract의 `code`(`llm_unavailable`)는 바꾸지 않고 새 공개 `code`도 추가하지 않았다. 대신 `LLMUnavailableError.__init__`에 내부 전용 `reason` 키워드 인자(기본값 `"provider_error"`)를 추가하고, `_create()`의 `except` 순서를 `RateLimitError`(`reason="rate_limited"`) → 그 외 `OpenAIError`(`reason="provider_error"`) 순으로 배치했다(`RateLimitError`가 `OpenAIError`의 하위 클래스이므로 순서가 중요하다). 설정 검증 실패는 `reason="configuration_error"`, 전체 호출 Timeout은 `reason="timeout"`, 빈 응답은 `reason="empty_response"`로 분류했다. `agent_service.py`에 `_llm_unavailable_message(exc)` Helper를 추가해 `reason=="rate_limited"`일 때만 재시도를 안내하는 메시지("LLM 사용 한도를 초과했거나 일시적으로 요청이 제한되었습니다. 잠시 후 다시 시도해 주세요.")를 반환하고, 그 외에는 기존 일반 메시지를 유지한다. `reason` 값 자체와 Provider 원문 오류는 API 응답에 노출하지 않는다.
* 추가한 회귀 테스트: `tests/test_llm_client.py`에 3개 추가(`test_llm_unavailable_error_defaults_to_provider_error_reason`, `test_complete_json_translates_rate_limit_error_without_leaking_message`, `test_complete_json_translates_empty_response_with_empty_response_reason`; 기존 SDK 오류·Timeout 테스트에도 `reason` Assertion을 추가). `tests/test_agent_service.py`에 2개 추가(`test_rate_limited_llm_keeps_public_code_but_returns_retry_message`, `test_generic_provider_error_keeps_default_llm_unavailable_message`).
* 실제 테스트 결과: `uv run pytest -q tests/test_llm_client.py tests/test_agent_service.py` → 통과 (35 passed: 15 + 20).
* Plan과의 차이: 없음(공개 `code` Enum 불변, `LLMUnavailableError`는 Plan이 "원본 오류를 노출하지 않는 안전한 예외로 변환한다"는 원칙만 정의하고 정확한 속성 구성은 구현 세부사항으로 남긴 범위 안에서 `reason` 속성을 추가했다).
* 현재 상태: `Resolved`(RateLimitError 분류 순서, 내부 reason, 안전한 전용 메시지와 회귀 테스트 확인)

## Codex 구현 최종 재검토 발견 사항(3차)

2차 수정 3건을 코드와 회귀 테스트로 재검토한 뒤 아래 High 발견 D·E를 기록했다. 이후 두 발견을 수정했고, Codex 4차 재검토에서 기존 공격 3건의 거부와 관련 회귀 테스트를 확인해 D·E를 `Resolved`로 판정했다.

### 발견 D — 필수 JOIN·HAVING 뒤의 `OR` 조건으로 의미 검증 우회(High)

* 실제 파일: `app/services/sql_guardrail.py`
* 발견 내용: `_JOIN_ON_PRODUCT_ID_PATTERN.search()`와 `_HAVING_BELOW_SAFETY_STOCK_PATTERN.search()`는 필수 표현식이 SQL 어딘가에 포함됐는지만 확인한다. 따라서 정상 SQL의 Join을 `ON p.ProductID = pi.ProductID OR 1 = 1`로, HAVING을 `HAVING SUM(pi.Quantity) < p.SafetyStockLevel OR 1 = 1`로 바꾼 두 경우가 모두 `validate()`를 통과했다. 첫 번째는 사실상 Product와 ProductInventory의 Cross Join이 되고, 두 번째는 안전재고 미달 Filter를 항상 참으로 만들어 전체 모집단을 반환할 수 있다.
* 영향: LLM이 생성한 SQL이 승인된 Join·Filter를 겉으로 포함하면서 실제 의미를 무력화해도 MCP 실행으로 진행된다. Fail Closed 원칙, 대표 질문의 승인 Join·Filter 정의와 `FR-007`~`FR-009`에 어긋난다.
* **실제 수정 내용**: `_JOIN_ON_PRODUCT_ID_PATTERN.search()`/`_HAVING_BELOW_SAFETY_STOCK_PATTERN.search()`를 완전히 제거하고, Clause 경계 기반 정확 일치 비교로 재작성했다. `_extract_clause_after(text, start_pattern)` Helper가 `ON`/`HAVING` 키워드 바로 뒤부터 다음 Clause 경계 키워드(`INNER`/`LEFT`/`JOIN`/`GROUP`/`HAVING`/`ORDER`) 직전 또는 문자열 끝까지의 원문을 추출한다. `_normalize_predicate(text)`가 대괄호와 모든 공백을 제거하고 대문자로 바꿔 canonical 형태를 만들고, 추출한 Clause 전체를 승인된 단일 Predicate(ON: `<Product alias>.ProductID=<ProductInventory alias>.ProductID`의 좌우 순서 허용 2종, HAVING: `SUM(<ProductInventory alias>.Quantity)<<Product alias>.SafetyStockLevel` 1종)와 완전 일치 비교한다. `OR 1 = 1` 같은 추가 조건은 canonical 문자열 뒤에 추가 문자가 붙어 완전 일치에 실패해 거부된다. Clause 경계 키워드 집합에서 `WHERE`를 의도적으로 제외했다 — ON/HAVING 뒤에 `WHERE`를 끼워 넣는 시도는 다음 경계(GROUP/ORDER)까지 그대로 흡수되어 완전 일치 비교에서 함께 거부되므로 별도 WHERE 금지 규칙 없이 같은 메커니즘으로 방어된다. Product/ProductInventory Alias의 좌우 순서가 바뀐 ON Predicate는 계속 허용한다(두 Alias가 실제로 정확한 Table을 가리키는지는 이미 확정된 `product_alias`/`inventory_alias`로 검증). 공개 시그니처는 바꾸지 않았고 SQL Parser·새 의존성은 추가하지 않았다.
* 추가한 회귀 테스트: `tests/test_sql_guardrail.py`에 `test_join_and_having_predicate_extensions_are_rejected`(Parametrize 4종: JOIN 뒤 `OR 1=1`, HAVING 뒤 `OR 1=1`, JOIN에 미승인 `AND` Predicate 추가, HAVING에 미승인 `AND` Predicate 추가) + `test_join_predicate_allows_reversed_alias_order_when_tables_are_correct`(좌우 순서가 바뀐 정상 Join은 계속 허용) 총 5개.
* 실제 테스트 결과: `.venv/Scripts/python.exe -m pytest -q tests/test_sql_guardrail.py` → 48 passed(수정 전 39개 전부 회귀 없이 통과 + 신규 9개). 수정 전 `validate()`를 직접 호출해 재현했던 `join_or_true`/`having_or_true` 두 우회 SQL도 이제 `SqlRejectedError`를 던짐을 별도로 재확인했다.
* 현재 상태: `Resolved`(Codex 4차 재검토에서 Clause 전체 일치 검증과 기존 우회 2건의 거부를 직접 확인)

### 발견 E — 출력 Alias와 물리 표현식의 연결을 검증하지 않음(High)

* 실제 파일: `app/services/sql_guardrail.py`
* 발견 내용: 현재 검증은 승인 출력 Alias 4종이 `output_aliases` 집합에 존재하는지만 확인한다. 정상 SQL의 `p.Name AS Name`을 `pi.Quantity AS Name`으로 바꿔도, 별도로 존재하는 정상 `SUM(pi.Quantity) AS CurrentInventory`와 나머지 Alias 때문에 전체 검증을 통과했다. 같은 방식으로 Alias 중복이나 다른 승인 Column을 잘못된 출력 이름에 연결해 결과 의미를 바꿀 수 있다.
* 영향: API가 `completed`로 반환하는 `columns` 이름과 실제 값의 의미가 달라질 수 있으며, 대표 결과의 제품명·현재 재고·안전재고 Contract와 `FR-008`·`FR-010`을 보장하지 못한다. 실제 Gemini E2E가 통과하더라도 비결정적인 다음 생성 SQL에 대한 Backend 강제가 되지 않는다.
* **실제 수정 내용**: `_SUM_QUANTITY_AS_CURRENT_INVENTORY_PATTERN`(CurrentInventory만 검사하던 기존 패턴)과 옛 `missing_output_aliases` 존재 여부 검사를 제거하고, SELECT 목록 전체를 정밀 파싱하는 로직으로 대체했다. `_extract_select_list(cleaned, top_match)`가 `TOP (n)` 직후부터 `FROM` 직전까지의 원문을 추출하고, `_split_top_level_commas(text)`가 `SUM(...)` 등 괄호 안의 콤마는 무시하면서 최상위 콤마로만 항목을 분리한다. 정확히 4개 항목이 아니면 즉시 거부한다. 각 항목을 `<expr> AS <alias>` 형태로 파싱해, (1) `alias`가 승인된 4개 이름(`ProductID`/`Name`/`CurrentInventory`/`SafetyStockLevel`) 중 하나가 아니면 거부, (2) 같은 `alias`가 이미 나왔으면(중복 선언) 거부, (3) `expr`을 `_normalize_predicate()`로 정규화한 값이 그 `alias`에 대해 승인된 물리 표현식(`ProductID`/`Name`/`SafetyStockLevel`은 `<Product alias>.<Column>`, `CurrentInventory`는 `SUM(<ProductInventory alias>.Quantity)`)과 정확히 일치하지 않으면 거부한다. 4개 항목이 모두 서로 다른 승인 이름에 정확히 바인딩돼야 통과하므로 중복·교환·미승인 5번째 표현식이 모두 구조적으로 차단된다. 기존 규칙 10(Table Alias 선언 밖의 모든 `AS X`가 승인된 이름인지 확인하는 전역 스캔)은 그대로 유지해 방어 계층을 이중으로 남겼다. 공개 시그니처는 바꾸지 않았고 SQL Parser·새 의존성은 추가하지 않았다.
* 추가한 회귀 테스트: `tests/test_sql_guardrail.py`에 `test_column_bound_to_wrong_output_alias_is_rejected`(`pi.Quantity AS Name`), `test_product_and_inventory_columns_swapped_across_output_aliases_is_rejected`(ProductID·Name 표현식 교환), `test_duplicate_required_output_alias_is_rejected`(ProductID 중복 선언으로 Name 누락), `test_extra_unapproved_output_expression_is_rejected`(승인된 5번째 출력 추가) 총 4개.
* 실제 테스트 결과: 위 발견 D와 같은 실행(`tests/test_sql_guardrail.py` 48 passed, 발견 D·E 신규 테스트 9개 모두 포함). 수정 전 `validate()`를 직접 호출해 재현했던 `wrong_output`(`pi.Quantity AS Name`) 우회 SQL도 이제 `SqlRejectedError`를 던짐을 별도로 재확인했다.
* 현재 상태: `Resolved`(Codex 4차 재검토에서 Alias-물리 표현식 결합 검증과 기존 우회의 거부를 직접 확인)

## Codex 구현 최종 재검토 발견 사항(4차)

발견 D·E 수정 결과를 코드·테스트와 직접 공격 재현으로 검토했다. JOIN/HAVING Clause 전체 일치 검증은 기존 `OR 1 = 1` 두 공격을 거부했고, SELECT Alias-물리 표현식 결합 검증도 `pi.Quantity AS Name` 공격을 거부했다. SQL Guardrail 집중 테스트 48개, Docker 대상 DB 테스트 10개, 실제 LLM을 제외한 전체 314개 테스트가 통과했으므로 발견 D·E는 `Resolved`로 판정한다.

### 발견 F — GROUP BY에 추가 Grain을 넣어 제품 단위 집계를 분할할 수 있음(High)

* 실제 파일: `app/services/sql_guardrail.py`
* 발견 내용: SELECT, JOIN과 HAVING은 승인 형태로 정밀 검증하지만 `GROUP BY` Clause는 전체 식별자 Allowlist만 통과하면 된다. 정상 SQL의 `GROUP BY p.ProductID, p.Name, p.SafetyStockLevel` 뒤에 `, pi.Quantity`를 추가한 SQL을 `validate()`에 직접 입력한 결과 잘못 승인됐다.
* 영향: `ProductInventory.Quantity`가 추가 그룹 키가 되면 제품별 위치 수량의 전체 합계가 Quantity 값별 부분 집계로 쪼개진다. 그 부분 집계에 안전재고 HAVING 조건이 적용되므로 제품 집합과 `CurrentInventory`가 Golden Query와 달라질 수 있다. 이는 FEAT-0004가 확정한 제품 Grain, 현재 재고의 `ProductID` 단위 합산, `FR-008`~`FR-010`을 Backend가 강제하지 못하는 문제다.
* 필요한 수정: `GROUP BY` Clause 전체를 추출해 Product Alias의 `ProductID`, `Name`, `SafetyStockLevel` 세 표현식만 정확히 한 번씩 포함하도록 검증해야 한다. 추가 그룹 키, 중복 키와 다른 Table Alias의 키는 Fail Closed로 거부하고, 허용할 표현식 순서 범위도 테스트로 명확히 고정해야 한다.
* 필수 회귀 테스트: `pi.Quantity` 추가 그룹 키 거부, 승인 Column을 이용한 다른 추가 그룹 키 거부, 필수 그룹 키 누락·중복 거부, 정상 대표 GROUP BY 통과. 표현식 순서 변경을 허용할지 여부는 현재 Prompt와 Week 1 범위를 기준으로 명시적으로 정해 테스트해야 한다.
* 재현(수정 전): 프로젝트 Windows 가상환경에서 기존 정상 SQL의 GROUP BY에 `pi.Quantity`를 추가한 뒤 `validate()` 직접 호출 → `group_by_quantity ACCEPTED`.
* **실제 수정 내용**: `app/services/sql_guardrail.py`에 `_GROUP_BY_KEYWORD_PATTERN`(`\bGROUP\s+BY\b`), `_NORMALIZED_ALIAS_COLUMN_PATTERN`(정규화된 문자열 전체가 `ALIAS.COLUMN` 형태와만 일치, 함수 호출·연산식·숫자 리터럴은 구조적으로 불일치), `_REQUIRED_GROUP_BY_COLUMNS = {"PRODUCTID", "NAME", "SAFETYSTOCKLEVEL"}`를 추가했다. `validate()`의 기존 ON-절(발견 D) 검증과 HAVING-절(발견 D) 검증 사이에 새 GROUP BY 검증 블록을 넣어 실제 SQL Clause 순서(FROM/JOIN...ON → GROUP BY → HAVING)와 맞췄다.
  * `GROUP BY` 키워드 등장 횟수를 `_GROUP_BY_KEYWORD_PATTERN.findall(cleaned)`로 먼저 세어, 0개면 "GROUP BY 없음"으로, 2개 이상이면 "중복 Clause"로 즉시 거부한다(부분 문자열 우회 방지 — `.search()`만 쓰면 첫 번째 Clause만 보고 뒤에 붙은 두 번째 GROUP BY를 놓친다).
  * 기존 발견 D에서 만든 `_extract_clause_after(cleaned, _GROUP_BY_KEYWORD_PATTERN)`를 그대로 재사용해 `GROUP BY` 바로 뒤부터 `HAVING` 직전까지의 원문만 추출한다(`_CLAUSE_BOUNDARY_PATTERN`에 이미 `HAVING`이 포함돼 있어 별도 경계 패턴 추가가 필요 없었다).
  * 기존 `_split_top_level_commas()`로 최상위 콤마 기준 분리 후, 항목 개수가 정확히 3개가 아니면 즉시 거부한다.
  * 각 항목을 기존 `_normalize_predicate()`(대괄호·공백 제거, 대문자 변환)로 정규화한 뒤 `_NORMALIZED_ALIAS_COLUMN_PATTERN`과 전체 일치하는지 확인 — 불일치(함수·연산식·숫자 등)는 거부.
  * 매치된 Alias가 기존 `table_alias_to_table`(발견 A에서 만든 alias→table 매핑)에서 `"PRODUCT"`를 가리키는지 확인 — ProductInventory Alias(`pi`) 등 다른 Table의 Alias는 거부.
  * 매치된 Column이 `_REQUIRED_GROUP_BY_COLUMNS`에 속하는지 확인 — Product의 다른 승인 Column(예: `p.Quantity`처럼 승인되지 않은 Column)은 거부.
  * `seen_group_by_columns: set[str]`에 추가하기 전에 이미 있는지 명시적으로 확인해 중복 그룹 키를 거부한다(집합 비교만으로는 중복이 개수 불일치로만 드러나 원인이 불명확해질 수 있어, 개수 확인과 별개로 중복 자체를 직접 확인).
  * 마지막으로 `_REQUIRED_GROUP_BY_COLUMNS - seen_group_by_columns`가 비어 있지 않으면 필수 그룹 키 누락으로 거부한다.
  * 세 표현식은 순서 없이 집합으로만 비교하므로 순서 변경은 자동으로 허용된다(요구사항 7). 대괄호 표기·공백·Alias 대소문자는 기존 `_normalize_predicate()`와 `table_alias_to_table`(대소문자 무관 조회)를 그대로 재사용해 계속 지원한다. 공개 시그니처 `validate(sql, context) -> str`는 바꾸지 않았고 새 의존성도 추가하지 않았다.
* **허용하는 정확한 형태**: `GROUP BY <Product alias>.ProductID, <Product alias>.Name, <Product alias>.SafetyStockLevel`(대괄호 표기·공백·Alias 대소문자 무관, 세 표현식의 나열 순서 무관). 예: `GROUP BY p.SafetyStockLevel, p.ProductID, p.Name`, `GROUP BY [p].[ProductID], [p].[Name], [p].[SafetyStockLevel]`, `GROUP BY P.ProductID, P.Name, P.SafetyStockLevel`(Alias `AS P`) 모두 통과.
* **거부하는 정확한 형태**: 승인된 세 표현식 외 어떤 추가·누락·중복도 거부 — `pi.Quantity` 등 ProductInventory Alias의 Column 추가, `p.Quantity` 등 Product의 비승인 Column 추가, `pi.ProductID`처럼 다른 Alias의 동일 이름 Column 추가, ProductID·Name·SafetyStockLevel 중 하나라도 누락, 같은 그룹 키 중복(예: `p.ProductID`를 두 번), 숫자 리터럴(`1`)·함수 호출(`SUM(p.SafetyStockLevel)`) 등 단순 `Alias.Column` 형태가 아닌 그룹 키, `GROUP BY` Clause 자체 누락, `GROUP BY` Clause가 두 번 이상 등장(중복 Clause를 통한 부분 문자열 우회 포함).
* **추가한 회귀 테스트**(`tests/test_sql_guardrail.py`, 총 14개 신규): `test_group_by_grain_violations_are_rejected`를 11개 케이스로 파라미터화(`group_by_quantity_attack`, `extra_approved_product_column_p_quantity`, `inventory_alias_productid_added`, `missing_required_productid`, `missing_required_name`, `missing_required_safety_stock_level`, `duplicate_group_key`, `numeric_literal_group_key`, `function_call_group_key`, `missing_group_by_entirely`, `duplicate_group_by_clause`) + 독립 통과 테스트 3개(`test_group_by_allows_reordered_required_keys`, `test_group_by_allows_bracket_notation`, `test_group_by_allows_mixed_case_product_alias`).
* **실제 테스트 결과**: `.venv/Scripts/pytest.exe -q tests/test_sql_guardrail.py` → 통과(62 passed — 수정 전 48개 + 이번 라운드 신규 14개). Fake 기반 전체 회귀 `.venv/Scripts/pytest.exe -q tests/ -m "not requires_llm and not requires_target_db"` → 통과(318 passed, 3 deselected). Docker 대상 DB `.venv/Scripts/pytest.exe -q tests/ -m "requires_target_db and not requires_llm"` → 통과(10 passed, 311 deselected — Docker Desktop이 이번 라운드에 실행 중이어서 실제로 재검증). 전체 회귀(`requires_llm` 제외) `.venv/Scripts/pytest.exe -q tests/ -m "not requires_llm"` → 통과(328 passed, 3 deselected).
* **직접 공격 재현(수정 후)**: `.venv/Scripts/python.exe -c <validate 직접 호출>`로 발견 D·E가 재현했던 `join_or_true`(JOIN 뒤 `OR 1 = 1`)·`having_or_true`(HAVING 뒤 `OR 1 = 1`)·`wrong_output`(`pi.Quantity AS Name`)와 발견 F의 `group_by_quantity`(GROUP BY에 `pi.Quantity` 추가) 4건을 모두 다시 입력 → 4건 모두 `SqlRejectedError`로 거부됨을 확인(수정 전에는 `group_by_quantity`만 `ACCEPTED`, 나머지 3건은 이전 라운드에 이미 거부로 확인됨).
* 현재 상태: `Resolved`(Codex 5차 재검토에서 제품 Grain 3개 강제, 정상 변형 허용, 기존 공격 4건 거부와 전체 회귀를 확인)

## Plan 준수 및 차이

Approved Plan과 일치한 결정:

* `.env` 로딩 방식과 FastAPI/MCP Settings 분리, `/api/questions` 전용 Validation Handler와 기본 Handler 위임, LLM Client Wrapper·내부 Instance Lifecycle(지연 생성·재사용·`aclose()` no-op), 응답 `code` Enum과 `extra="forbid"` 불변조건, Backend SQL 12개 규칙(순서 포함), `LLMClient` Protocol 주입 경계, `requires_llm`의 `RUN_LLM_TESTS`+`is_configured()` 이중 조건, Fake Physical Catalog 확장 — 이전 두 차례 Codex 재검토에서 Plan에 반영된 모든 결정을 코드로 그대로 옮겼다.
* HTTP 상태 코드 매핑(`completed`/`clarification_required`→200, `rejected`→422, `failed`→500), `QUERY_TIMEOUT_SECONDS=10`/`MAXIMUM_RETURNED_ROWS=100`, Correlation ID 발급 지점(Handler 또는 Router).
* `plan_validator.validate(plan, context) -> QueryPlan`과 `sql_guardrail.validate(sql, context) -> str`의 공개 시그니처(Plan 공개 경계 문서화 그대로) — 여러 라운드에 걸쳐 내부 검증 로직(Table Alias `alias -> table` 매핑, 이번 라운드의 Clause 완전 일치·출력 Alias-표현식 결합 검증)을 강화했지만 시그니처는 한 번도 바꾸지 않았다.
* 공개 Contract의 `code` Enum(`llm_unavailable` 포함) — 내부 `reason` 속성을 추가했지만 공개 `code` 자체는 바꾸지 않았다.

구현하지 못했거나 명시적으로 제외한 Plan 항목:

* 없음 — Plan이 정의한 모든 파일과 공개 경계를 구현했고, `TASK-013`의 실제 Gemini E2E 최종 확인도 완료했다.

Plan 수정·재승인이 필요했던 차이와 처리 결과:

* **Token 상한(RuntimeIntent 500→2000, QueryPlan 800→3000, SQL 600→2000)은 Approved Plan이 명시적으로 확정한 수치와 다른 구현이었다(발견 5·B).** 코드 값은 실제 Gemini 호환성 근거가 있어 되돌리지 않되, `plan.md` 본문의 확정값 자체를 실제 구현값으로 동기화하고 변경 근거를 기록해 차이를 해소했다. Approved Plan의 확정값을 바꾸는 변경이므로 그 시점에는 `plan.md`의 `Status`를 임의로 `Approved`로 유지하지 않고 `Draft`(Codex 재검토 대기)로 되돌렸다. **이번 라운드에 사용자가 동기화된 내용을 확인하고 `plan.md`를 다시 `Approved`로 재승인했다** — Plan Status의 부수적인 안내 문구도 재승인 사실에 맞게 정리했다.
* 발견 D·E(SQL Guardrail의 JOIN/HAVING Clause 완전 일치 검증, 출력 Alias-물리 표현식 결합 검증)는 Plan 재승인이 필요하지 않다고 판단했다. 그 외 차이(RuntimeIntent·QueryPlan Prompt 문구 추가, `QueryPlanInvalidError` 정의 위치, `plan_validator.py`/`sql_guardrail.py`의 검증 강화 전체(발견 1·2·3·A·D·E), `LLMUnavailableError`의 내부 `reason` 속성 추가(발견 C))도 마찬가지다. Plan이 "Private Helper" 또는 일반 원칙("SQL은 MCP 호출 전 Backend 자체 최소 검증을 통과해야 한다")만 정의하고 정확한 항목·강도·속성 구성을 구현 세부사항으로 남긴 범위 안의 조정이며, 공개 경계·Contract·보안 경계를 바꾸지 않는다.

## Feature 전체 검증

* [x] 모든 Spec 요구사항이 실제 구현과 검증에 연결됨
* [x] 모든 Plan 설계가 구현 또는 명시적으로 제외됨(제외 항목 없음)
* [x] 관련 자동 테스트 통과(328 passed — `requires_llm` 3건 제외 전체. Fake 기반 318개 + 실제 Docker MSSQL 10개, 이번 라운드도 Docker가 실행 중이어서 함께 재확인. 발견 F 수정으로 `test_sql_guardrail.py`가 48→62개로 증가)
* [x] 필요한 수동 검증 완료 — 실제 Gemini+Docker MCP Golden Query E2E 3건 통과
* [x] 실행하지 못한 검증과 남은 위험 기록(아래 참고)
* [x] 필수 Codex 구현 검토 완료 — 발견 D·E·F 수정과 관련 회귀·직접 공격 재현을 모두 확인

## 최종 구현 검토

1차 Codex 구현 검토에서 5건, 2차 재검토에서 3건이 나왔고 각각 수정됐다. 3차 재검토의 D·E는 4차에서, 4차 재검토의 F는 5차 재검토에서 수정과 회귀 테스트를 확인해 모두 `Resolved`로 판정했다. 이후 실제 Gemini Golden Query E2E 3건도 통과해 Feature를 `Verified`로 변경했다.

| Reviewer | 발견 사항 | 심각도 | 처리 Task 또는 기각 근거 | 상태 |
|---|---|---|---|---|
| Codex(1차) | 고정 Demo Scope의 필수 QueryPlan 의미(필수 Filter·Metric·Join)가 `plan_validator.validate()`에서 강제되지 않음 | High | `TASK-006`, 발견 1: 필수 항목 강제 검증 추가, Fake 기반 회귀 테스트 통과 | Resolved |
| Codex(1차) | Metadata ID가 존재하기만 하면 종류(Entity/Dimension/Metric/Filter/Grain/Join)가 달라도 통과함 | High | `TASK-006`, 발견 2: 종류별 검증으로 교체, Fake 기반 회귀 테스트 통과 | Resolved |
| Codex(1차) | QueryPlan에서 Filter를 강제해도 생성 SQL에서 안전재고 조건이 누락될 수 있음 | High | `TASK-007`, 발견 3: 발견 D의 Clause 완전 일치 비교까지 포함해 수정과 회귀 테스트 확인 | Resolved |
| Codex(1차) | Golden Query E2E에서 제품명(`Name`)을 비교하지 않음 | Medium | `TASK-013`, 발견 4: 4개 필드 비교 로직과 실제 Gemini E2E 3건 통과 확인 | Resolved |
| Codex(1차) | Token 상한의 Plan 차이 기록이 부정확함("Plan이 수치를 고정하지 않았다"는 잘못된 설명) | Medium | `TASK-002`, 발견 5: 설명 정정과 Plan 본문 동기화 확인 | Resolved |
| Codex(2차) | 잘못된 JOIN(Alias가 실제로 어떤 Table을 가리키는지 미확인)이 SQL Guardrail을 우회함 | High | `TASK-007`, 발견 A: Alias→Table 검증과 중복 참조 거부 확인. 별도 `OR` Predicate 우회는 발견 D로 추적 | Resolved |
| Codex(2차) | Approved Plan의 Token 상한 확정값(500/800/600)이 실제 구현값(2000/3000/2000)과 동기화되지 않음 | Medium | `plan.md`, 발견 B: Token 상한·근거 동기화 확인. 이번 라운드에 사용자가 Plan을 재승인함 | Resolved |
| Codex(2차) | LLM 할당량 초과(Rate Limit)를 사용자가 다른 LLM 실패와 구분하지 못함 | Medium | `TASK-002`/`TASK-008`, 발견 C: 분류 순서·내부 reason·안전 메시지와 5개 회귀 테스트 확인 | Resolved |
| Codex(3차) | 필수 ProductID Join·안전재고 HAVING 뒤에 `OR 1 = 1`을 붙이면 정규식 의미 검증을 우회함 | High | 발견 D: Clause 경계 기반 완전 일치 비교, 직접 공격 재현 거부와 회귀 테스트 5개 확인 | Resolved |
| Codex(3차) | 출력 Alias 존재만 확인해 승인 물리 표현식과의 연결이 바뀐 SQL을 허용함 | High | 발견 E: SELECT Alias-표현식 정밀 결합 검증, 직접 공격 재현 거부와 회귀 테스트 4개 확인 | Resolved |
| Codex(4차) | GROUP BY에 `pi.Quantity`를 추가하면 제품 Grain 집계가 분할되지만 Guardrail이 승인함 | High | 발견 F: 승인된 Product 그룹 키 3개만 정확히 한 번씩 허용하고 추가·누락·중복·다른 Alias·함수/숫자를 거부. 순서·대괄호·대소문자 정상 변형과 공격 4건 재현 확인 | Resolved |

## 최종 검증 기록

| 검증 | 명령 또는 방법 | 결과 |
|---|---|---|
| FEAT-0004 신규 단위 테스트(전체) | `uv run pytest -q tests/test_metadata_service.py tests/test_llm_client.py tests/test_intent_resolver.py tests/test_metadata_retriever.py tests/test_query_planner.py tests/test_plan_validator.py tests/test_sql_guardrail.py tests/test_agent_service.py tests/test_api_query.py` | 통과 (133 passed — 1차 121개 + 2차 12개) |
| 2차 라운드 수정 대상만(발견 A·C) | `uv run pytest -q tests/test_sql_guardrail.py tests/test_llm_client.py tests/test_agent_service.py -m "not requires_llm"` | 통과 (74 passed: 39+15+20) |
| 전체(`requires_llm`·`requires_target_db` 제외) | `uv run pytest -q -m "not requires_llm and not requires_target_db"` | 통과 (295 passed, 13 deselected) |
| 실제 Docker MSSQL | `uv run pytest -q -m requires_target_db` | **이번 라운드는 실행하지 못함** — 로컬 Docker Desktop이 기동되어 있지 않음(`docker ps` 확인, 이 Feature와 무관한 환경 문제). 이전 라운드에는 10 passed, 3 skipped로 통과했었다(변경된 4개 파일이 MCP 실행 경로 자체를 건드리지 않으므로 회귀 위험은 낮게 평가하지만 실측은 아님) |
| 실제 Gemini Golden Query E2E | `RUN_LLM_TESTS=1 uv run pytest -q -m "requires_target_db and requires_llm"` | **이번 라운드는 실행하지 않음(사용자 지침 — 무료 할당량 미소비)**. 직전 라운드(2026-07-23 22:28 KST) 결과는 3 failed(전부 `llm_unavailable`, 할당량 소진) — 통과로 표현하지 않음 |
| 전체 회귀(`RUN_LLM_TESTS` 미설정, 이번 라운드) | `uv run pytest -q -m "not requires_llm and not requires_target_db"` | 통과 (295 passed, 13 deselected) |
| Codex 3차 재검토 집중 테스트 | `.venv/Scripts/pytest.exe -q tests/test_sql_guardrail.py tests/test_llm_client.py tests/test_agent_service.py -m "not requires_llm"` | 통과 (74 passed) |
| Codex 3차 재검토 전체 회귀 | `.venv/Scripts/pytest.exe -q -m "not requires_llm and not requires_target_db"` | 통과 (295 passed, 13 deselected, 기존 Starlette deprecation warning 1건) |
| Codex 3차 SQL Guardrail 우회 재현 | `.venv/Scripts/python.exe -c <validate 직접 호출>` | 3건 모두 잘못 승인됨: Join `OR 1=1`, HAVING `OR 1=1`, `pi.Quantity AS Name` |
| Codex 3차 서식 확인 | `git diff --check`; 변경 Feature 문서 2개의 후행 공백 검색 | 저장소 전체 `git diff --check`는 이번 검토와 무관한 기존 CRLF 변경 파일들 때문에 미통과. `plan.md`·`tasks.md` 후행 공백은 없음 |
| `requires_llm` 자동 Skip 재확인 | `uv run pytest -q tests/test_e2e_golden_query.py` | 통과 (3 skipped) |
| Python 문법·Import | `python -m py_compile app/services/sql_guardrail.py app/services/llm_client.py app/services/agent_service.py tests/test_sql_guardrail.py tests/test_llm_client.py tests/test_agent_service.py` + `import` 확인 | 통과 |
| 서식 — 공백 오류 | `git add -N`로 신규 파일 표시 후 `git diff --check`, 이후 `git reset` | 통과(CRLF 정보성 경고만, 오류 없음) |
| Secret 미노출 | `.env`의 `LLM_API_KEY`/`MSSQL_SA_PASSWORD`/`TARGET_DB_PASSWORD` 값을 읽어(출력하지 않고) 이번 라운드에서 변경·추가한 모든 파일에서 원문 포함 여부 정적 검색 | 통과(발견 없음) |
| 변경 파일 범위 | `git status --porcelain` | 이번 라운드는 `app/services/sql_guardrail.py`, `app/services/llm_client.py`, `app/services/agent_service.py`, `tests/test_sql_guardrail.py`, `tests/test_llm_client.py`, `tests/test_agent_service.py`, `docs/features/0004-natural-language-query-walking-skeleton/plan.md`, `docs/features/0004-natural-language-query-walking-skeleton/tasks.md`만 수정. Plan이 금지한 `app/db/`, `app/models/`, `mcp_server/`, FEAT-0001~0003 문서, `spec.md`, 기존 Contract/ADR/Architecture/Roadmap 미변경 확인. `docs/contracts/*`, `docs/mvp/roadmap.md`, `.env.example`은 이 작업 시작 전부터 있던 기존 사용자 변경이며 이번에도 손대지 않음 |
| 문서 링크 | 이 파일과 `plan.md`의 상대 링크 확인 | 통과 |
| 발견 D·E 수정 라운드 — SQL Guardrail 집중 테스트 | `.venv/Scripts/python.exe -m pytest -q tests/test_sql_guardrail.py -v` | 통과 (48 passed — 수정 전 39개 + 발견 D·E 신규 9개) |
| 발견 D·E 수정 라운드 — Fake 기반 전체 회귀 | `.venv/Scripts/python.exe -m pytest -q tests/ -m "not requires_llm and not requires_target_db"` | 통과 (304 passed, 13 deselected) |
| 발견 D·E 수정 라운드 — 실제 Docker MSSQL | `.venv/Scripts/python.exe -m pytest -q tests/ -m "requires_target_db and not requires_llm"` | 통과 (10 passed, 307 deselected) — 이번 라운드는 Docker Desktop이 실행 중이어서 실제로 재검증했다 |
| 발견 D·E 수정 라운드 — 전체 회귀(`requires_llm` 제외) | `.venv/Scripts/python.exe -m pytest -q tests/ -m "not requires_llm"` | 통과 (314 passed, 3 deselected) |
| 발견 D·E 우회 SQL 재검증 | `.venv/Scripts/python.exe -c <validate 직접 호출>`(발견 D·E가 재현했던 `join_or_true`/`having_or_true`/`wrong_output` 3개 SQL을 그대로 재사용) | 3건 모두 `SqlRejectedError`로 거부됨을 확인(수정 전 3건 모두 `ACCEPTED`였음) |
| 발견 D·E 수정 라운드 — Python 문법·Import | `python -m py_compile app/services/sql_guardrail.py tests/test_sql_guardrail.py` + `import app.services.sql_guardrail` | 통과 |
| 발견 D·E 수정 라운드 — 후행 공백 | `grep -n ' $' app/services/sql_guardrail.py tests/test_sql_guardrail.py` | 통과(매치 없음) |
| 발견 D·E 수정 라운드 — 서식 오류 | `git add -N app/services/sql_guardrail.py tests/test_sql_guardrail.py docs/features/0004-natural-language-query-walking-skeleton/` 후 `git diff --check`, 이후 `git reset` | 통과 — 이번 라운드 변경 파일에서 실제 공백/서식 오류 없음(기존 CRLF 개행 변환 경고만 출력되며, 이는 이번 변경과 무관한 저장소 전체의 기존 상태다) |
| 발견 D·E 수정 라운드 — Secret 미노출 | `.env`의 `LLM_API_KEY`/`TARGET_DB_PASSWORD`/`MSSQL_SA_PASSWORD` 값을 읽어(출력하지 않고) 이번 라운드 변경 파일 2개에서 원문 포함 여부 정적 검색 | 통과(발견 없음) |
| 발견 D·E 수정 라운드 — 변경 파일 범위 | `git status --porcelain` | 이번 라운드는 `app/services/sql_guardrail.py`, `tests/test_sql_guardrail.py`, `docs/features/0004-natural-language-query-walking-skeleton/plan.md`(Status 필드 정리), `docs/features/0004-natural-language-query-walking-skeleton/tasks.md`만 수정. `app/db/`, `app/models/`, `mcp_server/`, `spec.md`, Contract/ADR/Architecture/Roadmap 미변경 확인 |
| Codex 4차 재검토 — SQL Guardrail 집중 테스트 | `.venv/Scripts/pytest.exe -q tests/test_sql_guardrail.py` | 통과 (48 passed) |
| Codex 4차 재검토 — 실제 Docker MSSQL | `.venv/Scripts/pytest.exe -q -m "requires_target_db and not requires_llm"` | 통과 (10 passed, 307 deselected, 기존 Starlette deprecation warning 1건) |
| Codex 4차 재검토 — 전체 회귀(`requires_llm` 제외) | `.venv/Scripts/pytest.exe -q -m "not requires_llm"` | 통과 (314 passed, 3 deselected, 기존 Starlette deprecation warning 1건) |
| Codex 4차 직접 공격 재현 | `.venv/Scripts/python.exe -c <validate 직접 호출>` | 기존 D·E 공격 3건은 모두 거부. GROUP BY에 `pi.Quantity`를 추가한 새 공격은 잘못 승인(`group_by_quantity ACCEPTED`) |
| 발견 F 수정 라운드 — SQL Guardrail 집중 테스트 | `.venv/Scripts/pytest.exe -q tests/test_sql_guardrail.py` | 통과 (62 passed — 수정 전 48개 + 이번 라운드 신규 14개) |
| 발견 F 수정 라운드 — Fake 기반 전체 회귀 | `.venv/Scripts/pytest.exe -q tests/ -m "not requires_llm and not requires_target_db"` | 통과 (318 passed, 3 deselected) |
| 발견 F 수정 라운드 — 실제 Docker MSSQL | `.venv/Scripts/pytest.exe -q tests/ -m "requires_target_db and not requires_llm"` | 통과 (10 passed, 321 deselected) — Docker Desktop이 이번 라운드에도 실행 중이어서 실제로 재검증(`data-agent-mssql` 컨테이너 확인) |
| 발견 F 수정 라운드 — 전체 회귀(`requires_llm` 제외) | `.venv/Scripts/pytest.exe -q tests/ -m "not requires_llm"` | 통과 (328 passed, 3 deselected) |
| 발견 F 수정 라운드 — 직접 공격 재현(수정 후) | `.venv/Scripts/python.exe -c <validate 직접 호출>`(`join_or_true`/`having_or_true`/`wrong_output`/`group_by_quantity` 4건) | 4건 모두 `SqlRejectedError`로 거부됨을 확인(수정 전에는 `group_by_quantity`만 `ACCEPTED`였음) |
| 발견 F 수정 라운드 — Python 문법·Import | `python -m py_compile app/services/sql_guardrail.py tests/test_sql_guardrail.py` + `import app.services.sql_guardrail` | 통과 |
| 발견 F 수정 라운드 — 후행 공백 | `grep -n ' $' app/services/sql_guardrail.py tests/test_sql_guardrail.py docs/features/0004-natural-language-query-walking-skeleton/tasks.md` | 통과(매치 없음) |
| 발견 F 수정 라운드 — 서식 오류 | `git add -N app/services/sql_guardrail.py tests/test_sql_guardrail.py docs/features/0004-natural-language-query-walking-skeleton/tasks.md` 후 `git diff --check`, 이후 `git reset` | 통과 — 이번 라운드 변경 파일에서 실제 공백/서식 오류 없음(기존 CRLF 개행 변환 경고만 출력, 이는 이번 변경과 무관) |
| 발견 F 수정 라운드 — Secret 미노출 | `.env`의 `LLM_API_KEY`/`TARGET_DB_PASSWORD`/`MSSQL_SA_PASSWORD` 값을 읽어(출력하지 않고) 이번 라운드 변경 파일 3개에서 원문 포함 여부 정적 검색 | 통과(발견 없음) |
| 발견 F 수정 라운드 — 변경 파일 범위 | `git status --porcelain` | 이번 라운드는 `app/services/sql_guardrail.py`, `tests/test_sql_guardrail.py`, `docs/features/0004-natural-language-query-walking-skeleton/tasks.md`만 수정. `plan.md`, `spec.md`, `app/db/`, `app/models/`, `mcp_server/`, Contract/ADR/Architecture/Roadmap과 이 작업 시작 전부터 있던 기존 사용자 변경 파일(`.env.example`, `app/core/config.py`, `app/core/lifespan.py`, `docs/contracts/*`, `docs/mvp/roadmap.md`, `main.py`, `pyproject.toml`, `uv.lock`, `tests/conftest.py` 등)은 손대지 않음 |
| Codex 5차 재검토 — SQL Guardrail 집중 테스트 | `.venv/Scripts/pytest.exe -q tests/test_sql_guardrail.py` | 통과 (62 passed) |
| Codex 5차 재검토 — 실제 Docker MSSQL | `.venv/Scripts/pytest.exe -q -m "requires_target_db and not requires_llm"` | 통과 (10 passed, 321 deselected, 기존 Starlette deprecation warning 1건) |
| Codex 5차 재검토 — 전체 회귀(`requires_llm` 제외) | `.venv/Scripts/pytest.exe -q -m "not requires_llm"` | 통과 (328 passed, 3 deselected, 기존 Starlette deprecation warning 1건) |
| Codex 5차 직접 공격 재현 | `.venv/Scripts/python.exe -c <validate 직접 호출>` | `join_or_true`/`having_or_true`/`wrong_output`/`group_by_quantity` 4건 모두 `SqlRejectedError`로 거부 |
| 최종 실제 Gemini E2E — 첫 실행 | Windows 프로세스에서 `RUN_LLM_TESTS=1`, `tests/test_e2e_golden_query.py` 실행 | 1 passed, 2 failed. 대표 질문 통과 후 표현 변형 2건은 안전한 `llm_unavailable` Rate Limit 응답 |
| 최종 실제 Gemini E2E — 재실행 | `.venv/Scripts/python.exe -c "import os, pytest; os.environ['RUN_LLM_TESTS']='1'; raise SystemExit(pytest.main(['-q', 'tests/test_e2e_golden_query.py']))"` | 통과 (3 passed in 17.24s). 세 질문 모두 실제 Gemini→Guardrail→MCP 실행 결과가 Golden Query 4개 필드 전체와 일치 |

실행하지 못한 검증과 남은 위험:

* **실제 Gemini E2E 완료**: `TASK-013` 참고. 최종 재실행에서 대표 질문과 두 한국어 표현 변형이 모두 강화된 Backend 검증을 통과하고 실제 MCP 결과가 Golden Query의 4개 필드 전체와 일치했다. 이 Feature 범위의 실제 Provider 호환성과 `FR-010`을 확인했다.
* **강화된 Backend 검증의 정상 출력 허용 확인**: 발견 3·A·D·E·F 전체가 반영된 상태에서 실제 Gemini가 생성한 세 SQL이 Guardrail을 통과했다. 다만 LLM 출력은 비결정적이므로 향후 다른 표현을 생성하면 의미상 동등한 SQL이 엄격한 Week 1 정규식 검증에서 거부될 가능성은 운영상 잔여 위험으로 남는다.
* **제품 Grain GROUP BY 강제 — Codex 재검토 완료**: 발견 F 참고. GROUP BY Clause가 승인된 Product 표현식 3개로만 구성되는지 검증하고 추가·중복·누락·다른 Alias·함수/숫자를 거부하는 구현과 테스트를 확인했다. 이 항목은 `Resolved`다.
* **Gemini 응답의 비결정성**: LLM 기반 RuntimeIntent·QueryPlan·SQL 생성은 매 호출마다 정확히 같은 결과를 보장하지 않는다. Prompt로 완화한 문제(어휘 고정, filter 포함 지시)와 여러 라운드에 걸쳐 추가한 Backend 강제 검증에도 불구하고, 다른 질문이나 다른 시점의 호출에서 유사한 패턴이 재발할 가능성은 배제하지 않는다.
* **Gemini 무료 등급의 일일 20회 요청 한도**: 개발·디버깅 중에도 쉽게 소진되며, 소진 이후 여러 세션에 걸쳐도 회복되지 않는 것을 관찰했다. 실제 검증이나 반복 개발 시 유료 등급 전환이나 충분한 시간 간격을 둔 재시도가 필요하다.
* **동시 다중 요청의 실제 부하 검증 없음**: FEAT-0003과 동일하게 이 Feature도 성능·부하 목표가 NFR에 없으므로 별도 측정을 하지 않았다.
* **AWS 배포 환경 검증 없음**: 로컬 Docker MSSQL과 로컬 `.env` LLM 설정으로만 검증했다(Plan 범위 밖).

## Verified 조건

* [x] 모든 필수 구현과 검증이 완료됨 — 실제 Gemini E2E 3건과 Docker MSSQL 재확인 완료
* [x] Spec Acceptance Criteria와 Plan 준수 여부가 확인됨(구현·Fake 기반 검증 기준)
* [x] Plan과의 차이가 모두 이 문서와 `plan.md`에 근거와 함께 기록됨(Token 상한 차이는 `plan.md`를 동기화하고 사용자가 재승인해 해소, 나머지는 Plan이 열어둔 구현 세부사항 범위 안 — 공개 경계·Contract·보안 경계를 바꾸지 않아 재승인이 필요한 다른 항목은 없음)
* [x] Codex 구현 검토 결과가 해결되거나 명시적으로 기각됨 — 발견 D·E·F 모두 `Resolved`
* [x] 실제 변경, 테스트 결과와 남은 위험이 Tasks 기록과 일치함
