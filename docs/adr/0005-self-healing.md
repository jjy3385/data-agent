# 0005. SQL 자동 복구 제한 (SQL Self-Healing Limit)

## 상태 (Status)

제안됨 (Proposed)

## 배경 (Context)

생성된 SQL은 스키마 (Schema) 모호성, 잘못된 조인 (Join) 또는 SQL 방언 (Dialect)
문제로 실패할 수 있다. 자동
재시도는 유용성을 높일 수 있지만, 반복적인 재생성은 안전하지 않은 동작을 감출 수
있다.

## 결정 (Decision)

SQL 실행이 실패하면 자동 복구 재생성 (Self-Healing Regeneration)을 최대 한 번만
시도할 수 있으며, 재생성된 SQL도 동일한 가드레일 (Guardrail)을 다시 통과해야 한다.

## 결과 (Consequences)

- 재시도 동작은 예측 가능하고 제한적이다.
- 재생성 후에도 가드레일 (Guardrail) 적용은 필수다.
- 지속적인 실패는 반복 재시도하지 않고 기록하여 사용자에게 알려야 한다.
