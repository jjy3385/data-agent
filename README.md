
---



# 🏢 B2B Slack SQL Data Agent (Enterprise-Grade)



본 프로젝트는 외래키(FK)가 누락되고 영문 약어로 오염된 한국형 레거시 기업 환경(ERP/그룹웨어 등)에서 비개발자가 안전하고 신뢰성 있게 데이터를 조회할 수 있도록 통제하는 'On-Premise 호환 AI 데이터 거버넌스 및 오케스트레이션 레이어'입니다.



이 문서는 개발자와 AI 코딩 에이전트가 4주간의 MVP 개발 중 스코프를 통제하고 길을 잃지 않기 위한 **마스터 아키텍처 가이드**입니다.



---



## 🎯 Target Test Environment (테스트 데이터 환경)



AI가 완벽하게 정제된 DB가 아닌, 현실의 지저분한 환경에서 작동함을 증명하기 위해 다음 데이터셋을 타깃으로 개발을 진행합니다.



* **Microsoft `AdventureWorks` DB:** 복잡한 엔터프라이즈 B2B 구조 시뮬레이션.

* **대한민국 공공데이터포털(data.go.kr) 및 Kaggle:** 국산 레거시 특유의 명명 규칙(`REG_DT`, `EMP_NO`, `DEPT_CD` 등)과 한글 주석이 혼재된 오염된 스키마 환경.



---



## 🧭 Design Principles (절대 원칙)



이 프로젝트를 작성하는 모든 개발자와 AI는 코드를 짤 때 다음 원칙을 최우선으로 적용합니다.



1. **Security before Intelligence:** AI의 영리함보다 백엔드의 철벽 통제가 먼저다.

2. **Policy before SQL:** 쿼리 실행 전, 유저 권한(ACL)과 테이블 접근 정책이 무조건 먼저 평가되어야 한다.

3. **Read-Only by Default:** 타깃 데이터베이스(MSSQL)는 어떠한 경우에도 수정/삭제 권한을 가지지 않는다.

4. **Explain Contextually (XAI):** AI가 데이터를 반환할 때, 어떤 공식과 기준으로 데이터를 뽑았는지 한글 요약문으로 함께 증명한다.

5. **Fail Closed, Not Open:** 쿼리 안전성이나 권한이 1%라도 의심스럽거나 에러가 발생하면 무조건 쿼리를 차단(Drop)한다.



---



## 🚫 Non-Goals (MVP 단계에서 절대 하지 않을 것)



4주 MVP의 성공적인 코어 엔진 런칭을 위해 **아래 항목들은 의도적으로 배제**합니다.



* **Next.js 기반의 Full Admin Portal:** 4주 차에는 FastAPI의 Swagger(Docs)나 간단한 Jinja2 템플릿, CLI 수준으로 어드민 기능을 대체하여 백엔드 코어에 리소스를 집중합니다.

* **Multi-Database 지원:** MVP는 오직 MSSQL만 타깃으로 합니다.

* **완벽한 회원가입/Auth 시스템:** 어드민 환경은 단일 마스터 패스워드나 `.env`로 통제합니다.



---



## 🏁 MVP Completion Criteria (MVP 완료 E2E 시나리오)



이 프로젝트의 MVP는 **다음의 시나리오가 끊김 없이(End-to-End) 작동할 때 완료**된 것으로 간주합니다.(예시) 



1. Slack 사용자가 "지난달 VIP 고객 미수금 현황 알려줘"라고 질문한다.

2. 시스템이 Slack ID를 기반으로 유저 직급(ACL)을 확인하고, 허용된 테이블만 스키마 컨텍스트에 포함한다.

3. 시스템이 '공공데이터포털' 스타일의 엉망인 스키마 속에서 'Virtual FK' 힌트를 통해 올바른 조인 관계를 찾아낸다.

4. AI가 생성한 SQL이 Guardrail(키워드 차단, TOP 100 제한)을 무사히 통과한다.

5. 타깃 MSSQL에서 데이터를 조회하고, 추출 기준(XAI)과 함께 슬랙에 반환한다.

6. 이 모든 과정과 생성된 SQL이 Admin DB `audit_logs`에 저장된다.

7. 사용자가 결과가 이상하다고 판단해 슬랙의 [🚨 오류 신고] 버튼을 누르면 `error_reports` 테이블에 즉시 적재된다.



---



## 🧠 8대 핵심 엔지니어링 스펙 (우선순위 기반)



### [P0 - 필수 코어 엔진]



1. **데이터-스키마 디커플링:** LLM에는 메타데이터만 전송. 실제 쿼리 실행 및 가공은 사내망 백엔드가 전담.

2. **플러그형 LLM 독립 구조:** `.env` 관리만으로 OpenAI 호환 API 기반의 프라이빗 LLM 스위칭 지원.

3. **조직도 기반 동적 권한 제어 (ACL):** 유저 직급에 따라 민감 데이터 스키마 원천 마스킹.

4. **다중 방어선 가드레일:** Read-Only 계정, 블랙리스트 키워드(`DROP` 등) 차단, 강제 `TOP N` Row Limit, 타임아웃 방어.

5. **설명 가능한 AI (XAI) 및 오류 신고:** 자연어 역번역(추출 기준 설명) 제공 및 슬랙 인터랙티브 오류 신고 큐(`error_reports`) 적재.



### [P1 - 레거시 대응 핵심 무기]



6. **한국형 가상 관계(Virtual FK) 추론 엔진:** FK가 없는 레거시 환경 극복을 위해 MSSQL 한글 주석 역공학 및 명명 규칙 기반 가상 조인 맵핑.

7. **에이전틱 복합 워크플로우 (Multi-turn):** 미수금 원천 추적 등 복잡한 실무를 위한 태스크 분해 로직.

* *제한 사항:* 무한 루프 방지를 위해 **최대 2-Depth**까지만 연쇄 추론 허용.

* *Self-Healing:* 쿼리 에러 발생 시 재생성은 **최대 1회**만 허용하며, 재생성된 쿼리도 반드시 가드레일을 다시 통과해야 함.







### [Phase 2 - 포스트 MVP 비전]



8. **토큰 비용 최적화:** Schema RAG 및 Semantic Caching 기능은 코어 엔진 안정화 이후 도입.



---



## 📅 4-Week MVP Roadmap & Progress Tracker



AI 에이전트는 [✅ 완료됨] 항목을 분석하고, [🏃 진행 중] 항목의 태스크에만 코딩 자원을 집중하십시오.



### [🏃 진행 중] Week 1: 코어 백엔드 & 스키마 인트로스펙션



* [ ] FastAPI 프로젝트 기본 구조 및 폴더 트리 설계.

* [ ] Admin DB (SQLite) 기초 DDL 정의 (`users`, `audit_logs`, `table_policies`, `error_reports`).

* [ ] Target DB(MSSQL - `AdventureWorks` 및 한국형 공공데이터 오염 구조) 시스템 카탈로그 및 주석 역공학 모듈.

* [ ] 메타데이터를 JSON Schema Context로 변환 및 ACL 기반 마스킹 레이어 구현.



### [🗓️ 예정] Week 2: AI 연동 & 가드레일 레이어



* [ ] LLM 호환 API 클라이언트 통신 모듈 구축.

* [ ] 가상 FK 힌트 결합 로직 고도화.

* [ ] 다중 방어선(Defense in Depth) 기반 SQL 검증 가드레일 레이어.

* [ ] 자연어 역번역 (XAI Plan) 생성 모듈 개발.



### [🗓️ 예정] Week 3: 에이전트 루프 & Slack 통합



* [ ] 최대 2-Depth / 1-Retry 제한이 걸린 에이전트 워크플로우 및 Self-Healing 로직 구현.

* [ ] Slack Bolt 연동 (웹훅 수신, 스레드 응답 반환, 오류 신고 버튼 이벤트 처리).

* [ ] Admin DB 감사 로그(`audit_logs`) 저장 파이프라인.



### [🗓️ 예정] Week 4: API 완성 및 E2E 테스트



* [ ] Admin 관리용(데이터 사전 CRUD, 오류 신고 조회) FastAPI End-point 구축 (UI는 Swagger로 대체).

* [ ] `MVP Completion Criteria`에 명시된 시나리오 E2E 통합 테스트.

* [ ] Docker Compose 작성 및 배포 환경 세팅.



---



## 💻 Tech Stack Directory Structure (FastAPI)



```

.

├── app/

│   ├── api/                  # API 라우터 (Slack, Admin)

│   ├── core/                 # 설정, 가드레일 규칙 (.env 등)

│   ├── db/                   # DB 세션 (admin_db.py, target_db.py)

│   ├── models/               # SQLAlchemy ORM (users, audit_logs 등)

│   └── services/             # 비즈니스 로직

│       ├── schema_service.py # 스키마 파싱, 마스킹, Virtual FK 결합

│       ├── llm_service.py    # LLM 통신 및 XAI Plan 생성

│       └── agent_service.py  # 2-Depth 추론 및 Self-Healing 통제

├── README.md                 # 본 설계 문서

└── main.py                   # FastAPI 진입점



```


---

## 🤝 AI-Assisted Development Protocol

이 프로젝트는 AI 코딩 에이전트를 적극 활용하지만, 설계권·검증권·승인권은 반드시 개발자가 가진다.

### Core Rules

1. **Architect First, AI Second**
   - 개발자가 먼저 타입, 인터페이스, 함수 시그니처, 책임 범위를 정의한다.
   - AI는 정의된 경계 안에서 구현을 보조한다.

2. **Atomic Task Delegation**
   - AI에게 한 번에 큰 기능을 맡기지 않는다.
   - 한 번의 요청은 하나의 함수, 하나의 쿼리, 하나의 테스트처럼 원자 단위로 제한한다.

3. **No Blind Copy-Paste**
   - AI가 생성한 코드는 반드시 읽고, 실행하고, 설명 가능해야 병합한다.

4. **Explain Every Line That Matters**
   - 이해하지 못한 코드, 라이브러리, 패턴은 즉시 AI에게 이유와 대안을 질문한다.

5. **Human Owns Architecture**
   - AI는 구현 보조자, 리뷰어, 테스트 작성자, 대안 제시자 역할을 한다.
   - 최종 설계 결정과 코드 승인 책임은 개발자에게 있다.

자세한 작업 방식은 `docs/development-protocol.md`를 따른다.


---

---

## 🤝 Expected Project Architecture

[Slack 메신저]
     ▲ (Webhook / Socket)
     ▼
┌────────────────────────────────────────────────────────┐
│ 1. AI Orchestrator 서비스 (FastAPI - agent_service.py)  │ 
│    = 【MCP 호스트 (Host) + MCP 클라이언트 (Client)】     │
└────────┬───────────────────────────────────────▲───────┘
         │ (HTTP REST API)                       │
         ▼                                       │ (MCP 프로토콜: JSON-RPC)
┌─────────────────────────┐                      │
│ 2. 단순 지능 모델        │                      ▼
│ (OpenAI API / 온프레미스)│             ┌────────────────────────┐
│ * MCP가 뭔지 모름!       │             │ 3. Data Engine 서비스   │
└─────────────────────────┘             │ (FastAPI - db_server)   │
                                        │ = 【MCP 서버 (Server)】 │
                                        └───────────┬────────────┘
                                                    │ (pyodbc)
                                                    ▼
                                            [ MSSQL 레거시 DB ]

---