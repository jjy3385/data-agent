# 0007. 대상 DB 실행을 위한 로컬 stdio MCP 경계

## 상태 (Status)

승인됨 (Accepted)

## 배경 (Context)

MVP와 로컬 시연은 개발 중에는 프로세스(Process) 내부에서 DB를 직접 호출하고 시연에서만 별도 MCP 경로를 사용하는 대신, 동일한 실행 아키텍처(Architecture)를 사용해야 한다.

FastAPI 백엔드(Backend)는 ACL 평가, Enterprise Metadata 검색, Query Plan 검증, SQL Guardrail, Workflow Depth 제어 및 Audit을 계속 통제하면서 대상 DB 실행은 재사용 가능한 Tool 경계 뒤로 분리한다.

MCP 튜토리얼(Tutorial)을 통해 로컬 Python MCP Server가 `stdio`를 통해 Typed Tool을 제공하고 Read-Only 애플리케이션 계정으로 AdventureWorks2022를 조회할 수 있음을 검증했다. 다만 운영용 FastAPI 애플리케이션이 MCP 프로세스(Process)의 Lifecycle과 실행 경계를 어떻게 소유할지는 정의하지 않았다.

## Roadmap 변경과 단계적 적용 (Staged Rollout)

이 ADR을 처음 작성할 때 전제한 Roadmap은 Security Foundation과 전체 Governance(ACL, RuntimeIntent·QueryPlan Validation, SQL Guardrail, Audit)를 MCP 실행 경계보다 먼저 갖추는 순서였다. 이후 채택한 현재 3주 MVP Roadmap은 순서를 바꿔, 먼저 자연어 질문이 실제 조회 결과까지 이어지는 Walking Skeleton(FEAT-0003·FEAT-0004)을 Week 1에 연결한 뒤 Week 2에 Governance를 강화한다([MVP Roadmap](../mvp/roadmap.md) 참고).

이 변경은 로컬 `stdio` MCP 경계 자체를 바꾸지 않는다. FastAPI가 대상 DB에 직접 연결하지 않고 승인된 MCP Tool을 통해서만 접근한다는 결정은 그대로 유지된다. 달라지는 것은 그 경계 앞에서 FastAPI가 수행하는 사전 검증(Pre-validation)의 범위이며, 이는 아래 "단계적 적용" 절에 따라 Week 1의 최소 안전 경계에서 Week 2의 전체 Governance로 단계적으로 확장된다. 최종 MVP는 두 Week가 끝난 뒤에도 기존 Governance 경계를 모두 적용하는 상태를 목표로 하며, 이 ADR은 그 경계를 약화시키지 않는다.

---

## 고려한 대안 (Alternatives Considered)

### A. FastAPI 내부에서 대상 DB 직접 실행

FastAPI가 Query Executor를 직접 호출하여 대상 DB와 통신한다.

장점은 구조가 단순하고 프로세스 관리가 필요 없다는 점이다.

그러나 개발 환경과 시연 환경의 실행 경계가 달라질 수 있으며, MCP가 선택적 기능으로 남게 된다. 본 프로젝트는 MCP를 실제 실행 경계로 사용하는 것을 목표로 하므로 채택하지 않았다.

### B. 원격(Remote) MCP Server

FastAPI와 별도의 MCP 서비스를 네트워크로 연결한다.

장점은 프로세스 분리와 수평 확장이 가능하다는 점이다.

그러나 서비스 간 인증, 원격 Transport, 장애 처리 및 운영 복잡도가 증가하므로 MVP 범위를 벗어난다.

---

## 결정 (Decision)

MVP에서 FastAPI 백엔드는 Workflow Orchestrator 역할을 담당하며 MCP Client와 MCP Server 하위 프로세스(Subprocess)의 Lifecycle을 관리한다.

FastAPI는 공식 MCP SDK의 Client를 사용하며 MCP Wire Protocol을 직접 구현하지 않는다.

다음 규칙을 적용한다.

1. **각 FastAPI 워커 프로세스는 하나의 로컬 MCP Server 하위 프로세스를 소유한다.** MVP는 FastAPI 워커 하나만 지원하며, 해당 워커는 애플리케이션 Lifespan 동안 하나의 MCP Server와 하나의 장기 유지(Long-lived) `stdio` MCP Client Session을 생성하여 모든 API 요청에서 재사용한다. 요청마다 새로운 MCP Server를 시작하지 않는다.

2. FastAPI 종료 시 MCP Session을 정상 종료하고 자식 프로세스를 종료한다.

3. MVP는 FastAPI 워커 하나와 MCP Server 프로세스 하나를 전제로 한다. Multi-Worker 배포는 지원하지 않는다.

4. 대상 DB 실행은 승인된 MCP Tool을 통해서만 수행한다. FastAPI 애플리케이션 서비스는 대상 DB에 직접 연결하지 않는다. 단, Admin DB는 본 규칙의 대상이 아니다.

5. FastAPI는 계속 Policy Enforcement Point 역할을 담당한다. 최종 MVP에서 MCP Tool을 호출하기 전에 ACL을 평가하고 Runtime Intent와 Query Plan Contract를 검증하며 SQL Guardrail을 수행하고 Audit을 기록한다. LLM의 Tool Call 제안만으로 SQL 실행 권한이 부여되지 않는다. 이 통제가 Week 1과 Week 2에 걸쳐 어떻게 단계적으로 확장되는지는 아래 "단계적 적용" 절을 따른다.

6. SQL 생성과 Query Plan-SQL 구조 검증은 FastAPI에서 완료한다. MCP Server는 Query Plan으로부터 SQL을 생성하지 않으며 FastAPI가 전달한 검증 완료 SQL만 실행한다.

7. MCP 실행 Tool은 자연어 질문, Runtime Intent, ACL 정보 또는 LLM Tool Call 원문을 입력으로 사용하지 않는다. MCP Tool은 검증 완료 SQL, 바인딩 Parameter, Correlation ID, Query Timeout 및 Maximum Returned Rows만 입력으로 사용한다.

8. MCP Server는 대상 DB 드라이버와 연결 Lifecycle을 소유하며 Read-Only 자격 증명, SELECT-Only 재검증, 다중 Statement 차단, Query Timeout, Maximum Returned Rows 및 최소 실행 안전성을 강제한다. 이는 FastAPI SQL Guardrail을 대체하지 않는 추가 방어 계층이다.

9. FastAPI는 애플리케이션 시작 시 MCP 초기화, Tool Discovery 및 필수 Tool Contract를 검증한다. Tool 이름뿐 아니라 기대하는 입력 Contract와의 호환성도 확인한다. MCP Server를 시작할 수 없거나 초기화 또는 Discovery가 실패하거나 필수 Tool Contract가 호환되지 않으면 애플리케이션 시작을 중단한다(Fail Closed).

10. 요청 처리 중 MCP 장애가 발생해도 FastAPI는 대상 DB 직접 실행으로 우회하지 않는다.

11. 운영용 MCP Server는 FastAPI가 관리하는 내부 실행 구성요소(Component)이다. 외부 또는 범용 LLM 애플리케이션에 직접 등록하지 않으며 검증된 Backend Workflow 밖에서 제한 없는 SQL 실행 Tool을 제공하지 않는다.

12. MVP Transport는 로컬 `stdio`만 지원한다. Streamable HTTP, Remote MCP 배포, 서비스 간 인증 및 Horizontal Scaling은 Post-MVP에서 검토한다.

13. MVP에서는 공유 MCP Client Session에 대한 대상 DB 실행 요청을 Backend에서 직렬화한다. Session Pool, Process Pool 및 병렬 DB 실행은 Post-MVP 범위로 둔다.

14. MCP Server는 `stdout`을 MCP Protocol 전용으로 사용한다. 일반 애플리케이션 로그와 진단 정보는 `stderr` 또는 별도 Log Sink를 사용한다.

15. 최종 MVP에서 FastAPI는 MCP Tool 호출 전 실행 시도와 MCP 응답 또는 오류를 실제 Workflow Audit에 연결한다. 이 Audit 연결은 Week 2의 FEAT-0006에서 적용하며 Week 1에는 별도 Audit 구현을 요구하지 않는다.

---

## 단계적 적용 (Staged Rollout)

로컬 `stdio` MCP 실행 경계와 아래 "항상 유지되는 경계"의 규칙은 Week 1부터 적용한다. ACL, RuntimeIntent·QueryPlan Validation, 전체 SQL Guardrail과 Workflow Audit은 Roadmap에 따라 단계적으로 적용하며, 최종 MVP에서는 전체 Governance 경계를 충족한다.

### Week 1

* [FEAT-0003 MCP Read-Only Data Access](../features/0003-mcp-readonly-data-access/spec.md)가 MCP 연결, Tool(`inspect_schema`, `execute_readonly_query`), Lifecycle과 MCP Server의 최소 실행 안전성을 구현한다.
* FEAT-0004는 Demo 사용자와 고정 Demo Scope를 사용한다.
* 단일 SELECT, 고정된 Table·Column 범위, Query 제한과 최소 Tool Contract 검증을 적용한다.
* 실제 Admin DB 사용자·역할·Table Policy 기반 ACL 전체는 아직 적용하지 않는다.
* MCP Server의 Read-Only 계정, SELECT-only 재검증, 다중 Statement 차단, Query Timeout과 Maximum Returned Rows는 Week 1부터 적용한다.
* MCP Tool은 공개 SQL Console로 노출하지 않는다.
* Correlation ID는 Tool 요청과 구조화된 결과·오류를 연결하는 요청 추적 식별자로 사용하되, 실제 Admin DB Workflow Audit 기록은 Week 1 범위에 포함하지 않는다.

### Week 2

* FEAT-0006에서 Admin DB 사용자·역할·Table Policy 기반 ACL을 적용한다.
* RuntimeIntent·QueryPlan Validation을 강화한다.
* SQL AST Guardrail, Allowlist, 승인 Join과 Plan-SQL Match를 적용한다.
* 실제 Workflow Audit 연결을 적용한다.

### 항상 유지되는 경계

Week와 무관하게 다음은 항상 유지된다.

* FastAPI의 대상 DB 직접 연결 금지
* MCP 장애 시 직접 DB Fallback 금지
* 공식 MCP SDK 사용, MCP Wire Protocol 미구현
* 로컬 `stdio` Transport
* 단일 FastAPI Worker와 단일 MCP Server
* 장기 유지 MCP Client Session
* Read-Only 대상 DB 계정
* MCP Server의 최소 실행 안전성(SELECT-only 재검증, 단일 Statement 차단, Query Timeout, Maximum Returned Rows)
* `stdout`은 MCP Protocol 전용
* Fail Closed(MCP 초기화·Tool Discovery·Contract 검증 실패 시 애플리케이션 시작 중단)

---

## 결과 (Consequences)

* 로컬 개발과 MVP 시연이 동일한 MCP 실행 경계를 사용한다.
* 대상 DB 자격 증명은 MCP Server 프로세스에만 주입되며 FastAPI 애플리케이션 서비스에서는 직접 접근하지 않는다.
* 대상 DB 접근 로직은 Typed MCP Tool Contract 뒤로 분리되어 독립적으로 테스트할 수 있다.
* FastAPI는 MCP 하위 프로세스 상태, 시작·종료 순서, Timeout, 오류 변환 및 `stdio` Lifecycle을 관리해야 한다.
* 통합 테스트는 MCP 시작 실패, Tool Contract 불일치, 요청 처리 중 연결 종료, Timeout, 정상 종료 및 Fail Closed 동작을 포함해야 한다.
* MVP는 FastAPI 워커 하나와 MCP Server 프로세스 하나를 전제로 한다.
* 공유 MCP Session을 직렬화하므로 동시에 여러 DB 실행 요청이 들어오는 경우 처리량은 제한된다.
* Worker 하나를 넘는 확장은 프로세스 소유권과 실행 경계를 다시 설계해야 하며, 별도 배포되는 MCP Service 또는 다른 명시적 실행 경계를 도입할 가능성이 높다.
* MCP를 사용할 수 없으면 직접 실행 대체 경로(Fallback)는 제공하지 않으며 항상 Fail Closed로 동작한다.

## 관련 문서

* [FEAT-0003 MCP Read-Only Data Access Spec](../features/0003-mcp-readonly-data-access/spec.md)
* [`inspect_schema` Contract](../contracts/inspect-schema.md)
* [`execute_readonly_query` Contract](../contracts/execute-readonly-query.md)
* [컴포넌트 책임과 경계](../architecture/component-boundaries.md)
* [질문 처리 시퀀스](../architecture/query-execution-sequence.md)
* [MVP Roadmap](../mvp/roadmap.md)
