# 0003. 가상 외래 키 (Virtual Foreign Keys)

## 상태 (Status)

제안됨 (Proposed)

## 배경 (Context)

레거시 (Legacy) 기업 데이터베이스에는 물리적 외래 키 (Physical Foreign Key)가 없을 수
있으며, 축약된 컬럼 이름이나 한글이 혼재된 주석을 사용하는 경우가 많다.

## 결정 (Decision)

시스템은 스키마 메타데이터 (Schema Metadata), 명명 규칙 및 데이터베이스 주석을
바탕으로 가상 외래 키 (Virtual Foreign Key) 힌트 (Hint)를 추론하고 관리한다.

## 결과 (Consequences)

- 대상 스키마 (Schema)를 변경하지 않고도 조인 (Join) 안내를 통해 SQL 생성을
  개선할 수 있다.
- 추론된 관계는 신뢰된 사실이 아니라 힌트 (Hint)로 취급해야 한다.
- Virtual FK 결정은 조회 및 감사 (Audit)가 가능해야 한다.
