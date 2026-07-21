# 아키텍처 결정 기록 안내 (ADR)

> 이 폴더는 프로젝트의 중요한 설계 결정을 왜 내렸는지 기록한다. 현재 형식이나 호출 순서보다 선택 이유, 대안과 결과를 확인할 때 읽는다.

## ADR 목록

| ADR | 결정 |
|---|---|
| [0001](0001-readonly-db.md) | 대상 업무 DB를 Read-Only로 제한 |
| [0002](0002-admin-db.md) | Governance용 Admin DB 분리 |
| [0003](0003-virtual-fk.md) | 관리자 승인 Virtual FK만 사용 |
| [0004](0004-agent-depth.md) | Agent Workflow Depth 제한 |
| [0005](0005-self-healing.md) | SQL Self-Healing 횟수 제한 |
| [0006](0006-result-handle.md) | Public LLM Result Handle을 Post-MVP로 연기 |
| [0007](0007-local-stdio-mcp-db-boundary.md) | 로컬 stdio MCP를 대상 DB 실행 경계로 사용 |

## 읽는 방법

ADR은 “왜”를 설명한다. 정확한 입출력 형식은 [Contract](../contracts/README.md), 현재 구성요소와 흐름은 [Architecture](../architecture/README.md)를 기준으로 한다. 결정이 바뀌면 기존 기록을 조용히 덮어쓰기보다 새 ADR로 대체 관계를 남긴다.
