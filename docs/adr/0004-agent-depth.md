# 0004. Agent Workflow 깊이 제한 (Agent Workflow Depth Limit)

## 상태 (Status)

제안됨 (Proposed)

## 배경 (Context)

다단계 추론 (Multi-Step Reasoning)은 실무 질문 처리에 유용하지만, 통제되지 않은
에이전트 반복 실행 (Agent Loop)은 지연 시간, 비용 및 운영 위험을 증가시킨다.

## 결정 (Decision)

MVP에서 에이전트 워크플로 (Agentic Workflow)의 최대 깊이 (Depth)를 2로 제한한다.

## 결과 (Consequences)

- 복잡한 작업은 보수적으로 분해해야 한다.
- 무제한 계획 및 실행 반복 (Loop)을 방지한다.
- 일부 고급 조사는 추가 질문이 필요하거나 Post-MVP 범위로 확장될 수 있다.
