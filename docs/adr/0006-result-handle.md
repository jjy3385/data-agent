# 0006. Public LLM 데이터 격리를 위한 Result Handle

## 상태 (Status)

Post-MVP 제안 (Proposed for Post-MVP)

## 배경 (Context)

MVP는 조직이 승인한 Private LLM만 사용하며 제한된 결과 투영 (Projection)만
전달한다. Public LLM을 지원하려면 원본 DB 결과 (Raw Database Result)와 모델에
제공되는 페이로드 (Payload) 사이에 더 강한 격리가 필요하다. Result Handle이 이
경계를 제공할 수 있지만, 저장, 권한 부여, 만료, 워크플로 범위 (Workflow Scope) 및
감사 요구사항은 4주 MVP 범위를 벗어난다.

## 결정 (Decision)

Result Handle 지원은 Post-MVP로 연기한다. 도입 시 Result Handle은 내부 Result
Store에 보관된 결과를 가리키는 불투명하고 (Opaque) 수명이 짧은 참조가 된다. 이를
데이터, SQL 또는 권한으로 취급하지 않는다.

다음 규칙을 반드시 적용한다.

1. 백엔드 (Backend)만 Handle을 해석 (Resolve)할 수 있다. LLM이나 Slack Client는 Handle로
   데이터를 조회할 수 없다.
2. Handle을 해석할 때마다 현재 ACL을 다시 검사한다. 발급 당시 권한만으로는
   충분하지 않다.
3. Handle은 Correlation ID, 워크플로 깊이 (Workflow Depth) 및 허용된 다음 행동에
   종속된다.
4. Handle은 짧은 시간 안에 만료되며 활성 워크플로 (Workflow) 중에만 유효하다.
5. Raw Result, Result Summary 및 LLM Projection은 분리하여 저장하고 관리한다.
6. LLM에는 현재 작업에 필요한 최소한의 Summary 또는 Projection만 전달한다.
7. Handle 발급, 해석 시도, 거부, 만료 및 삭제를 감사한다.

## 결과 (Consequences)

- MVP에서는 Result Store, Handle 발급 및 Handle 해석을 구현하지 않는다.
- MVP의 Private LLM에는 제한 없는 원본 결과 (Raw Result)가 아니라 TOP N과 허용
  컬럼이 적용된 투영 (Projection)만 전달한다.
- 이 설계와 보안 테스트가 구현되기 전까지 Public LLM의 결과 처리를 비활성화한다.
- Handle은 요청 간에 재사용할 수 없으며, 임의 SQL 생성이나 설정된 한도를 넘는
  워크플로 깊이 (Workflow Depth)에도 사용할 수 없다.

## 관련 문서

- [Result Projection Contract](../contracts/result-projection.md)
- [XAI Payload Contract](../contracts/xai-payload.md)
- [MVP 범위](../mvp/scope.md)
