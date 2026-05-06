# Claude Code 인수인계 메모

작성일: 2026-05-04 (최종 갱신: 2026-05-06 5차)
환경: Claude.ai → Claude Code (현재 작업 환경: 데스크탑 kj77k)

---

## 즉시 해야 할 일 (Claude Code 새 세션 시작 시)

다음 파일을 순서대로 읽고 시작:

1. `Claude_Code_인수인계.md` (이 파일) — 전체 완료 이력
2. `Claude_Code_인수인계_추가.md` — vibe 8개 카테고리, 챗봇 흐름 정의
3. `vibe_매핑_설계.md` — vibe 모듈 설계 + 학술 근거
4. `phase7_챗봇_웹앱_설계.md` — 챗봇 + 웹앱 작업 지시서

**현재 상태: 챗봇 웹앱 로직 버그 수정 완료, 추천 엔진 정상 동작 확인 중**

---

## 1. 프로젝트 한 줄 요약

**서울살이 v5** — 서울 거주지 추천 시스템. 2026 서울시 빅데이터 활용 경진대회 창업부문 출품 (마감 5/13, 1차 발표 5/22).

3축 Fuzzy TOPSIS (통근 + 주거비 + 인프라) + 청년정책 통합. 3단계 계층적 필터링 (구 → 동 → 매물).

---

## 2. 완료된 작업 이력

### 환경 설정 작업

- **환경변수 분리 완료**: API 키 6개 → `.env` 파일로 분리 (Git 제외)
- **노트북 경로 교체 완료**: `kj77k` → `JangKyoungJun` (housing_recommendation_v5.py, feedback_module.py)
- **백업 생성**: `*_backup.py` 3개 (gitignore 제외)
- **Git repo 신규 생성**: `https://github.com/kj77kj7/housing_recommendation.git`

### v5 코드 정상화 작업

**Baseline 검증 완료**: scenario1~4 정상 동작 확인 (데스크톱에서 2026-05-03)

**혼잡계수/정적 CSV 제거 완료** (총 -222줄)
- 정적 파일 경로 5개 제거: 지하철 배차간격, 버스 도착정보, 환승인원, 환승역 거리, 버스노선 정보
- 혼잡계수 테이블 3개(CAR/BUS/SUBWAY) + coeff 함수 3개 제거
- CSV 로드 함수 5개 + lookup 빌드 함수 5개 제거
- `calculate_adjusted_transit_time()` 함수 제거
- `calc_commute_both_ways()`: 파라미터 5개 제거 (sw_wait, sw_load, tr_time, bus_stop, bus_route_hw), ODsay pathTime 직접 사용
- 데이터 한계 안내에서 "혼잡계수: TOPIS 통계 기반" 문구 제거
- 검증: ODsay IP 등록 후 시나리오1 정상 (성동구 3개 매물 추천, 최단 11분)

**자가용 API 전환 완료**: v1/directions → v1/future/directions
- `_next_weekday_at()` 헬퍼 추가 (출발 시각 → YYYYMMDDHHMM 변환)
- `get_drive_route_kakaomobility()`: departure_time 파라미터 추가, future/directions 분기
- `calc_commute_both_ways()`: 출근/퇴근 시각을 각각 departure_time으로 전달

**변경 후 재검증 완료**: 시나리오1(대중교통) + 시나리오2(자가용) 모두 정상
- 자가용: 송파구 200개 매물, future/directions API 출근/퇴근 시각 별도 계산 정상
- 대중교통: ODsay 정상
- git 커밋: `585b983`

### vibe 시스템 구축 작업

**vibe_module.py 신규 생성 완료** — 8개 카테고리 × 7종 인프라 가중치 시스템
- `VIBE_RAW_SCORES`: 1~5 척도 (Jacobs 1961 + KCI 논문 + AHP-TOPSIS 참고)
- 8개 카테고리: 조용함, 번화함, 청년활기, 가족친화, 자연친화, 편의 우선, 운동·건강, 카페·문화
- `normalize_weights()`: sum=7 정규화
- `get_vibe_weights(vibe_list)`: 다중 vibe 평균 가중치
- `extract_vibe_from_text(text)`: 키워드 매칭 폴백
- `apply_vibe_to_infra_scores(raw_scores, vibe_weights)`: 가중 평균

**housing_recommendation_v5.py에 vibe 통합 완료**
- `from vibe_module import get_vibe_weights, apply_vibe_to_infra_scores` 추가
- `calc_infra_score()`: `vibe_weights=None` 파라미터 추가, 가중 평균 분기
- `run_recommendation()`: `vibe_list=None`, `chatbot_mode=False` 파라미터 추가

**vibe_매핑_설계.md 작성 완료** — 설계 근거 및 학술 출처 정리

### 청년정책 시스템 개선 작업

**점수 산식 개편 완료**
- 정책 점수 = 월 절감액 합계 / 사용자 예산 × 100 (상한 100점)
- `analyze_benefit()` 신규: 혜택 유형 자동 분류 (월세지원/보증금/공공임대/기타)

**중복 수혜 경고 추가 완료**
- `detect_dup_limit(p)`: 지원 내용에 "중복 불가" 키워드 탐지
- 확인된 정책 중 중복 가능성 있으면 경고 출력

**`print_policy_section()` 개편 완료**
- ★ 신뢰도 표시 (확실/불확실), URL 출력, 자동매칭 라벨

**테스트 모드 추가 완료**
- `_TEST_MODE = False` (True 시 API 호출 없이 mock 3건으로 동작)
- `MOCK_POLICIES`: 서울시 청년 월세지원 / 마포구 보증금 / 행복주택 3건
- `auto_confirm=False` 파라미터: True 시 input() 없이 자동 선택 (챗봇 모드)
- `test_v5_auto.py` 수정: `_TEST_MODE = True` 설정으로 API 호출 없이 시나리오3 검증

**검증 완료**: 시나리오3 (청년정책 포함) — 점수/중복경고/섹션 출력 모두 정상

### 챗봇 + 웹앱 통합 작업

**vibe → v5 인프라 점수 가중치 실제 연결 확인 완료**

**llm_module.py 신규 생성 완료** — Gemini 2.5 Flash-Lite 슬롯 추출
- 모델: `gemini-2.5-flash-lite` (분당 15회, 일 1,000회 무료)
- `google.genai` 패키지 사용 (`google.generativeai` deprecated → 교체 완료)
- 폴백 5종 시나리오 구현:
  - API 키 없음 → 즉시 폴백
  - 네트워크 오류 / 5xx → 지수 백오프 3회 후 폴백
  - JSON 파싱 실패 → 1회 재시도 후 폴백
  - 일일 한도 초과 → 즉시 폴백
  - 분당 한도 초과 → 4초 대기 후 재시도
- `prompts/slot_extraction.txt` 외부 프롬프트 파일 분리

**nlp_input_module.py 신규 생성 완료**
- `ChatBot` 클래스: 슬롯 수집 상태머신 (MAX_TURNS=25)
- 필수 슬롯 7개: work_address / transport_mode / rent_type / deposit_manwon / allowed_minutes / house_type / weight_preference
- LLM 추출 → 컨텍스트 인식 폴백 (봇이 물어본 슬롯 기억 후 직접 할당)
- vibe / use_youth_policy 선택 슬롯 처리
- `get_v5_params()`: 슬롯 → run_recommendation() kwargs 변환

**FastAPI 백엔드 완료** (`webapp/`)
- `webapp/main.py`: `/api/chat`, `/api/recommend`, `/api/health` 엔드포인트
- `webapp/run.py`: `python -m webapp.run` → http://localhost:8000
- 세션 관리: UUID 기반 인메모리 (프로세스 재시작 시 초기화)

**HTML + Vanilla JS 프론트엔드 진행 중**
- `webapp/static/index.html`, `style.css`, `app.js`
- 피그마 디자인 반영 (챗봇 말풍선 / 빠른 옵션 / 우측 진행도 패널)
- 사이드바 비활성 메뉴는 "준비 중" 처리

**버그 수정 완료**: Gemini 모델명 오류 (`gemini-2.5-flash-lite-preview-06-17` → `gemini-2.5-flash-lite`)

**좀비 서버 프로세스 문제 해결**: `--reload` 옵션 사용 시 구버전 worker 프로세스가 남아 요청을 처리하는 현상 발생.
- 해결 절차 확립: python 프로세스 전체 종료 → `__pycache__` 전체 삭제 → `uvicorn ... --host 0.0.0.0 --port 8000` (`--reload` 없이) 재시작
- 이 절차를 **코드 수정 후 매번** 반드시 수행

### 챗봇 로직 버그 수정 작업 (2026-05-05)

**Fix 3: vibe 파싱 강화**
- `nlp_input_module.py` `_parse_vibe_choice()`: 숫자(①~⑨) 매핑 외에 "상관없음", "조용함" 등 텍스트 이름 직접 검색 3번째 폴백 추가
- `webapp/main.py` `_quick_options_for()`: vibe 버튼이 청년정책 질문 중 표시 안 되도록 `and not bot._asked_policy` 조건 추가

**Fix 2: vibe 자유 텍스트 폴백**
- `process()` vibe 블록: `_parse_vibe_choice()` 실패 시 `extract_vibe_from_text()` 호출하는 추가 폴백 삽입

**Fix 5: 직장 주소 검증 + 카카오 geocode fallback**
- `SLOT_QUESTIONS["work_address"]`: "역명·건물명 불가" 안내 문구 추가
- `_validate_work_address()` 신규: 역명(`강남역`) / 건물명(`코엑스`, `타워` 등) 패턴 입력 시 오류 메시지 반환 후 재질문
- `housing_recommendation_v5.py` `clean_work_address()`: "302-에이32호" 한글+숫자 혼합 상세주소 패턴 제거 정규식 추가
- `geocode_address_kakao_with_fallback()` 신규: clean 후 실패 시 토큰 잘라가며 최소 3토큰까지 재시도. `run_recommendation()` 직장 주소 지오코딩 호출 위치에서 이 함수로 교체

**Fix 1: "직접 설정" 가중치 옵션**
- "알아서 해줘(위임)" → "직접 설정(직접설정)" 으로 교체 (질문 텍스트·버튼·파싱 로직 전부)
- `_parse_weight_custom()` 신규: "통근 70 주거비 30" / "7:3" 형식 파싱 → `[a, b]` 반환
- `_next_question()`: 직접설정 선택 후 비율 미입력 시 추가 질문
- `get_v5_params()`: 직접설정 시 입력 비율 → `weight_commute / weight_housing` 계산
- `_build_summary()`: "직접설정 (통근 N : 주거비 N)" 형식으로 표시

**추가 버그 수정 (2026-05-05)**

| 수정 | 파일 | 내용 |
|------|------|------|
| vibe 버튼 5→9개 | `webapp/main.py` | 가족친화·자연친화·편의 우선·운동·건강 버튼 추가 |
| 월세 질문 순서 | `nlp_input_module.py` `_missing_required()` | `deposit_manwon` 직후 `monthly_manwon` 질문하도록 순서 변경 |
| 보증금 파싱 | `nlp_input_module.py`, `llm_module.py` | `_parse_manwon()` 신규: 5천만원·5천·1억5천 등 다양한 표현 통합 처리 |
| 통근 시간 파싱 | `nlp_input_module.py`, `llm_module.py` | `_parse_commute_minutes()` 신규: 편도/왕복 구분, 1시간 30분, 한시간 반 등 처리. 비현실적 값(5분 미만, 300분 초과) 필터링 |
| CSV 파일 선택 | `webapp/main.py` | glob 패턴 `*.csv` → `*주거비*.csv` (교통 관련 CSV 잘못 로드 방지) |

**추천 결과·청년정책·주소 검증 버그 수정 (2026-05-05 2차)**

| 수정 | 파일 | 내용 |
|------|------|------|
| 추천 결과 전부 0 | `webapp/main.py` `_df_to_list()` | 컬럼명 전면 수정: `topsis_score`→`final_score`, `예상_통근시간(분)`→`commute_time_min`, `환산보증금(만원)`→`conv_deposit_manwon`, `주택유형`→`housing_type`. stage2 fallback 컬럼도 OR 체인 처리 |
| 청년정책 항상 테스트모드 | `webapp/main.py` | `youth_policy_module._TEST_MODE = True` 강제 설정 2곳 제거 (실제 API 호출 정상화) |
| 역명 입력 시 재질문 안 됨 | `nlp_input_module.py` `process()` | LLM 추출 `work_address`도 머지 전 `_validate_work_address()` 검증. 무효 시 `new_slots`에서 제거 + `_last_asked_slot="work_address"` 유지 → 재질문 정상 동작 |
| 통근시간 숫자만 입력 | `nlp_input_module.py` `_parse_commute_minutes()` | 순수 숫자 입력(`^\s*(\d+)\s*$`) → 분으로 처리하는 폴백 추가. "80" → 80분 인식. 5~300분 필터 동일 적용 |

### 청년정책 흐름 연결 — JWT + 챗봇 슬롯 실 데이터 연결 (2026-05-06 4차)

**배경**: 로그인 JWT의 나이/성별이 `bot.user_meta`에 이미 저장되어 있었으나, `get_v5_params()`는 여전히 하드코딩 더미값(`age=29, employment=재직`)을 사용하고 있었음. 이를 제거하고 실제 데이터로 연결.

**구현 내용 (`nlp_input_module.py`)**

| 항목 | 내용 |
|---|---|
| `POLICY_SLOTS` | 5개 서브슬롯: policy_employment / policy_income / policy_marriage / policy_education / policy_no_house |
| `POLICY_QUESTIONS` | 각 슬롯별 한국어 질문 + 번호 선택지 |
| `SLOT_DISPLAY` | 5개 슬롯 한글 레이블 추가 |
| 파서 4개 신규 | `_parse_employment_choice()`, `_parse_marriage_choice()`, `_parse_education_choice()`, `_parse_no_house_choice()` — 번호(①~⑤) + 텍스트 양방향 파싱 |
| `process()` fallback | `_last_asked_slot`이 policy_* 슬롯이면 해당 파서 호출 (policy_income은 `_parse_manwon()` 재사용) |
| `_next_question()` | `use_youth_policy=True` 후 POLICY_SLOTS 순서대로 None인 슬롯 질문 (employment → income → marriage → education → no_house) |
| `get_v5_params()` | 하드코딩 더미 완전 제거. `age = self.user_meta.get("age")` (JWT), 나머지는 슬롯 값 사용 |
| `_build_summary()` | 청년정책 반영 시 "나이 N세 \| 취업상태 \| 소득 N만원 \| ..." 상세 출력 |
| `slot_status()` | `use_youth_policy=True`인 경우 5개 슬롯 UI 패널에 추가 표시 |

**구현 내용 (`webapp/main.py`)**

| 항목 | 내용 |
|---|---|
| `_quick_options_for()` | policy_employment (5개 버튼) / policy_marriage (미혼·기혼) / policy_education (4개) / policy_no_house (무주택·주택소유) 빠른 선택 버튼 추가 |

**검증 결과**
- `use_youth_policy=True` 선택 후 5개 슬롯 순차 질문 ✅
- `user_info["age"]` = JWT user_meta 값 (로그인 나이 26세 → 그대로 반영) ✅
- 모든 policy 슬롯 수집 후 `_next_question() → None` (Done 처리) ✅
- `get_v5_params()` 에서 하드코딩 제거, 실 데이터 연결 ✅

**git 커밋**: `5c8b7d9` — feat: 청년정책 흐름 연결

---

### 청년정책 흐름 개편 1단계 — 회원가입 취업상태·학력 필드 추가 (2026-05-06 5차)

배경: 청년정책 자격 조건 중 "자주 안 바뀌는" 취업상태·학력 2개를 회원가입 시 수집. 챗봇에서 매번 묻지 않도록 하는 개편의 1단계. 챗봇 흐름 변경은 2단계에서 진행.

| 파일 | 변경 내용 |
|------|-----------|
| `webapp/static/signup.html` | 취업상태 라디오 3개(취업자/미취업자/자영업자) + 학력 라디오 4개(고졸이하/대학재학/대졸/석박사) 추가. 프론트 유효성 검사 + fetch body에 employment/education 포함 |
| `webapp/static/auth.css` | `.radio-group`, `.radio-item`, `.radio-label`, `.radio-desc`, `.auth-required` 스타일 추가 |
| `webapp/auth.py` | `SignupRequest`에 employment/education 필드 추가. 서버측 유효값 검증. INSERT SQL 확장. 회원가입/로그인 JWT 페이로드에 두 필드 포함 |
| `webapp/database.py` | `init_db()` 자동 마이그레이션에 `employment`, `education` 컬럼 추가 (기존 DB도 무중단 마이그레이션) |
| `webapp/main.py` | `bot.user_meta`에 `employment`, `education` 두 필드 추가 |

**저장 값 규칙**
- 취업상태: `"취업자"` / `"미취업자"` / `"자영업자"` (3개 고정)
- 학력: `"고졸이하"` / `"대학재학"` / `"대졸"` / `"석박사"` (youth_policy_module.py `_EDU_ORDER` 키와 일치)
- 카카오 로그인 사용자 / 기존 회원은 두 컬럼 NULL → 단계 2에서 챗봇이 청년정책 진입 시 물어볼 예정

**다음 단계 (미착수)**
- 단계 2: 챗봇 청년정책 흐름 개편 (공통 자격 1차 필터 → 정책 카드 표시 → 사용자 선택 → 추가 조건만 묻기)
  - `nlp_input_module.py`의 `POLICY_DETAIL_ORDER`, `_ask_policy_xxx` 등 변경 예정
  - user_meta.employment/education → policy 1차 필터에 활용 예정

**git 커밋**: (이번 세션 커밋 예정)

---

### 인증 시스템 통합 + git UI 매칭 (2026-05-05 3차)

배경: 회원가입 정보(생년월일·성별)를 청년정책 1차 매칭에 활용하기 위해 로그인/회원가입 도입. UI는 https://github.com/min05ji26/Seoul_housing 레포에 맞춤.

**UI 신규 페이지 (Vanilla HTML/CSS/JS, React 미사용)**

| 파일 | 내용 |
|------|------|
| `webapp/static/login.html` | 카카오 시작 버튼 + divider + 비밀번호 찾기 링크. 카카오 콜백 token 쿼리 처리 |
| `webapp/static/signup.html` | 카카오 시작 버튼 + divider. 닉네임/이메일/비번/생일/성별 입력 |
| `webapp/static/forgot-password.html` | 3단계 마법사 (이메일→6자리코드→새비번), 5분 타이머 |
| `webapp/static/auth.css` | 신규. `.kakao-btn(#FEE500)`, `.auth-divider`, `.code-input`, `.timer-row` 등 |
| `webapp/static/index.html` | 토큰 없으면 `/login` 리다이렉트, 로그아웃 버튼, 닉네임 표시. 브랜드 "서울살이"→"집찾봇" |
| `webapp/static/app.js` | `getAuthHeaders()` 헬퍼 추가, `/api/chat`·`/api/recommend` 호출 시 `Authorization: Bearer` 자동 첨부 |

**백엔드 라우터 (모두 신규)**

| 파일 | 내용 |
|------|------|
| `webapp/database.py` | sqlite3 직접 사용 (SQLAlchemy 미사용 — greenlet/C++ 컴파일러 회피). `users.kakao_id` 컬럼 + `checklist_items`/`search_conditions`/`recommendation_history` 테이블. `_column_exists()` 자동 마이그레이션 |
| `webapp/auth.py` | `/auth/signup`, `/auth/login`, `/auth/kakao`, `/auth/kakao/callback`. JWT 페이로드에 birth_date/gender/age/nickname 포함. `decode_token()` 헬퍼로 `/api/chat`에서 토큰→`bot.user_meta` 주입 |
| `webapp/password.py` | `/password/send-code`(6자리, 10분 만료), `/password/verify-code`, `/password/reset-password`. Gmail SMTP 미설정 시 콘솔에 코드 출력 (개발모드) |
| `webapp/user.py` | `/user/{id}` 내정보, `/user/{id}/nickname` PATCH, `/user/{id}/conditions` 검색조건, `/user/{id}/recommendations` 추천이력 |
| `webapp/checklist.py` | `/checklist` GET/POST/PATCH/DELETE. 첫 GET 시 13개 기본 항목 자동 시드 |
| `webapp/main.py` | 4개 라우터 등록, `/login`·`/signup`·`/forgot-password` GET 추가. `/api/chat`에서 Authorization 헤더→token→bot.user_meta 주입 |
| `nlp_input_module.py` | `ChatBot.__init__`에 `self.user_meta: Dict[str,str] = {}` 추가. JWT의 birth_date/gender/age 받아서 청년정책 1차 적용 가능 |

**bcrypt 호환성 버그 수정**

증상: 회원가입 시 500 Internal Server Error. `passlib 1.7.4`가 백엔드 초기화 시 72바이트 초과 시크릿으로 자체 검증을 시도하는데 `bcrypt 4.x`가 이를 거부 → `ValueError: password cannot be longer than 72 bytes`.

해결:
- `webapp/auth.py`, `webapp/password.py`: `passlib` 의존 제거, `bcrypt` 직접 사용
- `_hash_password()` / `_verify_password()` 헬퍼: UTF-8 인코딩 후 72바이트 자르기 직접 처리

**검증 결과**:
| 케이스 | 결과 |
|---|---|
| 신규 회원가입 | ✅ 200 + JWT + user_id |
| 중복 이메일 | ✅ 400 |
| 정상 로그인 | ✅ 200 + JWT |
| 틀린 비번 | ✅ 401 |
| DB 저장 | ✅ DBeaver에서 users 테이블 직접 확인 |

**의존성 추가**: `python-jose`, `bcrypt` (passlib 제거 권장)

**git 제외 추가**: `*.db`, `*.sqlite`, `*.sqlite3` (사용자 데이터 보호)

---

## 3. 핵심 결정 사항

### 교통 데이터 처리
- 자가용: 카카오모빌리티 **future/directions API** (시간대별 혼잡 자동 반영)
- 대중교통: **ODsay 그대로**, 혼잡도 보정 일체 없음
- 혼잡계수 테이블 3개(CAR/BUS/SUBWAY) 모두 **제거**

### 정적 파일
- **유지: 1개** — `주거비_데이터_최종통합버전.csv` (97MB, 597,797건)
  - 1·2단계 자치구·동 단위 시세 분포 통계 산출용
  - 갱신 주기: 반기 1회
- **제거: 5개** (지하철 배차간격, 버스 도착정보, 환승인원, 환승역 거리, 버스노선 정보)

### AI 기능
- 자연어 입력 챗봇 (Gemini Flash-Lite 슬롯 추출 → JSON → v5 파라미터)
- vibe 카테고리 매핑 (8개 카테고리, Jacobs 1961 + KCI 논문 + AHP-TOPSIS 근거)
- 청년정책 자동 매칭 + 점수 산식

### 챗봇 슬롯 (확정)
- **필수 슬롯 7개**: work_address, transport_mode, rent_type, deposit_manwon, allowed_minutes, house_type, weight_preference
- **조건부 슬롯**: monthly_manwon (월세 시), weight_custom (직접설정 시)
- **선택 슬롯**: region_filter, vibe (9개 다중 가능, 상관없음 포함), use_youth_policy

### UI 프레임워크
- **FastAPI 백엔드 + HTML/Vanilla JS 프론트** (RaceLab 구조 차용)
- 모바일 반응형: max-width 540px + viewport 메타태그
- PWA는 마감 후로

### LLM 호출
- Gemini 2.5 Flash-Lite 무료 티어 (분당 15회, 일 1,000회)
- 별도 `llm_module.py` + 외부 프롬프트 파일
- 폴백: 정규식 기반 (vibe_module의 extract_vibe_from_text 등)

---

## 4. API 키 설정 (신규 PC 작업 시 필수)

- `.env` 파일은 Git에 없음 (보안상 제외)
- 새 PC에서 작업 시작 시: `.env` 파일을 별도로 받아서 프로젝트 루트에 위치
- `.env` 전송: USB / 메신저 직접 전송 / 비밀번호 관리자
- `.env.example` 파일에 키 목록 있음 (값은 비워져 있음)
- **현재 키 목록**: KAKAO_LOCAL_REST_API_KEY / KAKAO_MOBILITY_REST_API_KEY / ODSAY_API_KEY / MOLIT_API_KEY / YOUTH_API_KEY / SEOUL_JOB_API_KEY / **GEMINI_API_KEY**

---

## 5. 향후 작업 항목 (메모)

- **경로 PC별 차이 문제**: `_DATA_DIR`, `SAVE_DIR`, `FEEDBACK_CSV_DIR`이 절대경로 하드코딩됨.
  git pull 시마다 경로 충돌 가능. 향후 (A) `.env`에 `PROJECT_ROOT` 추가 또는 (B) `__file__` 기준 상대경로 리팩토링 필요.
- **PWA 적용**: 마감 후 진행
- **사이드바 다른 메뉴 구현**: 주거 추천, 지도뷰, 이사 체크리스트, 예산 생활비, 내 정보 (마감 후)

---

## 6. 슬롯 스키마 (현재 사용 중)

```python
SLOT_SCHEMA = {
    # 필수 7개
    "work_address": str,           # 직장 주소
    "transport_mode": str,         # "car" | "transit"
    "rent_type": str,              # "전세" | "월세"
    "deposit_manwon": int,         # 보증금
    "monthly_manwon": int,         # 월세 (전세 시 None)
    "allowed_minutes": int,        # 허용 통근시간
    "house_type": str,             # "오피스텔" | "연립다세대" | None(둘다)
    "weight_preference": str,      # "통근우선" | "주거비우선" | "균형" | "직접설정"
    
    # 조건부 슬롯
    "monthly_manwon": int,         # 월세 시 필수
    "weight_custom": list[int],    # 직접설정 시 [통근비율, 주거비비율] (예: [70, 30])
    
    # 선택 슬롯
    "region_filter": str,          # 지역 (예: "강남구")
    "depart_time": str,            # "HHMM"
    "arrive_time": str,            # "HHMM"
    "vibe": list[str] | None,      # 9개 카테고리 다중 가능 (상관없음 → 빈 리스트)
    "vibe_unrecognized": str | None,
    "use_youth_policy": bool,

    # 청년정책 세부 슬롯 (use_youth_policy=True 후 수집)
    "policy_employment": str,      # "재직자"|"자영업자"|"미취업자"|"프리랜서"|"일경험없음"
    "policy_income": str,          # 월 소득 만원 단위 (예: "250")
    "policy_marriage": str,        # "미혼"|"기혼"
    "policy_education": str,       # "고졸이하"|"대학재학"|"대졸"|"석박사"
    "policy_no_house": str,        # "y"=무주택 / "n"=주택소유
}
```

---

## 7. vibe 카테고리 (9개)

| vibe | 버튼 번호 | 매칭 표현 예시 |
|---|---|---|
| 조용함 | ① | 조용한, 한적한, 고즈넉한, 사람 적은 |
| 번화함 | ② | 번화한, 활기찬, 시끌벅적, 사람 많은 |
| 청년활기 | ③ | 젊은 사람 많은, 20대, 활기찬 |
| 가족친화 | ④ | 가족, 아이 키우기 좋은, 안정적 |
| 자연친화 | ⑤ | 공원 가까운, 녹지, 산책 |
| 편의 우선 | ⑥ | 마트·편의점 가까운, 생필품 편한 |
| 운동·건강 | ⑦ | 헬스장 가까운, 운동 시설 많은 |
| 카페·문화 | ⑧ | 카페 많은, 디저트, 문화 공간 |
| 상관없음 | ⑨ | → vibe = [] (빈 리스트, 인프라 가중치 미적용) |

매칭 실패 표현 (역세권/학세권/치안/신축 등) → `extract_vibe_from_text()` 추가 폴백 후 실패 시 재질문

---

## 8. 주의사항 & 함정

### 주의 1: 사용자 작업 스타일
- "내가 묻기 전엔 먼저 묻지 말 것"
- "방향 결정 전 무작정 코드부터 올리지 말 것"
- "답변이 너무 길면 안 됨" — 핵심만 짚어서 짧게
- "답변 불가능 상황에서 토큰 낭비하지 말 것"
- 큰 변경(파일 삭제/함수 제거)은 적용 전 확인받기

### 주의 2: API 키 보안
- 절대 GitHub 등에 노출 금지 (`.env` 분리 완료)
- 환경변수 사용 중

### 주의 3: 절대 경로 문제
- v5 코드의 일부 경로가 Windows 절대 경로
- 데스크탑(`kj77k`) ↔ 노트북(`JangKyoungJun`) 이동 시 경로 수정 필요

### 주의 4: 메모리 부담
- 주거비 CSV 97MB, 597,797행 로드
- FastAPI에서 매번 재로드 안 되도록 캐싱 또는 모듈 레벨 로드 권장

### 주의 5: 카카오 future/directions API
- `departure_time` 형식: `YYYYMMDDHHMM` (12자리, 분 단위)
- `traffic_state`, `traffic_speed` 필드 추가됨

### 주의 6: .env 파일 가로채기
- AnySign4PC 같은 한국 보안 프로그램이 .env 확장자 가로채는 경우 있음
- 파일 연결을 메모장 또는 VSCode로 명시 권장

### 주의 7: LLM 호출 한도
- Gemini Flash-Lite 무료: 분당 15회, 일 1,000회
- 시연 중 한도 도달 시 자동 폴백 (사용자에게 안 보임)
- 콘솔 로그로만 한도 모니터링

### 주의 8: uvicorn 서버 재시작 절차 (캐시 문제 방지)
코드 수정 후 반드시 아래 순서로 재시작할 것. `--reload` 사용 금지 (좀비 worker 프로세스 발생):
```powershell
Get-Process python | Stop-Process -Force  # 모든 Python 프로세스 종료
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force
python -m uvicorn webapp.main:app --host 0.0.0.0 --port 8000  # --reload 없이
```

### 주의 9: 사용_csv_모음 폴더 관리
- 주거비 CSV 외 교통 관련 CSV(버스/지하철 등)는 이 폴더에 두면 안 됨
- `webapp/main.py`의 glob 패턴이 `*주거비*.csv`로 고정되어 있으므로 주거비 파일명에 "주거비" 포함 필수
- 현재 유효 파일: `주거비_데이터_최종통합버전.csv` (97MB, 597,797건)

### 주의 10: 직장 주소 입력 제한
- 역명(`강남역`)·건물명(`코엑스`, `타워` 등) 입력 시 챗봇이 오류 메시지 반환 후 재질문
- 내부적으로 `_validate_work_address()` + `geocode_address_kakao_with_fallback()` 이중 방어

### 주의 11: passlib + bcrypt 4.x 호환성
- `passlib 1.7.4`는 `bcrypt 4.x`와 호환 안 됨. 회원가입 시 500 에러로 나타남
- `passlib.context.CryptContext` 사용 금지. `bcrypt` 패키지 직접 사용 (`bcrypt.hashpw`, `bcrypt.checkpw`)
- 비밀번호는 UTF-8 인코딩 후 `[:72]`로 잘라서 전달 (bcrypt 72바이트 제한)

### 주의 12: SQLAlchemy 미사용 정책
- `greenlet`이 C++ 컴파일러를 요구해서 Windows 노트북 환경에서 설치 실패
- `sqlite3` 표준 라이브러리만 사용. ORM 필요시 raw SQL로 작성
- DBeaver는 `webapp/housing.db` 경로로 SQLite 연결해서 GUI 확인 가능

### 주의 13: DBeaver 데이터 새로고침
- 좌측 트리에서 테이블 클릭만으로는 데이터 패널 자동 갱신 안 됨
- 테이블 우클릭 → "데이터 편집" / "Read Data" 더블클릭, 또는 SQL Editor에서 `SELECT * FROM users` 직접 실행
- 데이터 패널 상단 탭 이름 확인 필수 (다른 테이블 보고 있는 경우 많음)

### 주의 14: 카카오 OAuth & Gmail SMTP는 옵션
- `KAKAO_CLIENT_ID` 미설정 시 `/auth/kakao` → 503 에러 (UI는 정상 표시)
- `EMAIL_ADDRESS`/`EMAIL_PASSWORD` 미설정 시 비밀번호찾기 코드를 콘솔에 출력 (개발모드)
- 실제 사용시 `.env`에 추가: Kakao Developers + Gmail 앱비밀번호 발급 필요

---

## 9. 마감 일정

- 경진대회 접수 마감: **2026-05-13 18:00** (남은 기간 약 1주)
- 1차 결과 발표: 2026-05-22

### 우선순위 (마감 우선)
1. **MUST**: HTML/CSS 디자인 완성 + 사용자 직접 테스트
2. **SHOULD**: 모바일 반응형 검증
3. **NICE**: Cloudflare Tunnel 외부 시연 준비
4. **DROP**: PWA / 사이드바 다른 메뉴 (마감 후)

---

## 10. 사용자가 좋아하는 작업 흐름

1. 결정 필요한 사항 명확히 제시 → 사용자 결정 → 다음 단계
2. 코드 변경은 "어디를 어떻게" 먼저 설명 → 동의 후 적용
3. 각 단계 완료 후 사용자가 직접 검증 가능하게 break point 만들기
4. 학술 근거나 신뢰성 있는 자료가 필요하면 web search로 검증
5. 사실/정의/시스템 동작에 대해 답변 전 반드시 코드·문서·웹 검색으로 확실한 검증을 거친 후 답변할 것 (추측·인상·이전 표현 답습 금지)

---

## 11. 다음 행동

Claude Code 새 세션에서:
1. 이 메모 읽었음을 확인
2. 사용자가 새 오류 리포트를 가져오면 해당 오류부터 처리
3. 오류 없으면 경진대회 마감(5/13) 전 남은 항목 확인:

**✅ 완료된 항목 (2026-05-06 기준)**
- 챗봇 슬롯 수집 / 추천 엔진 / 청년정책 매칭
- vibe 8개 카테고리 통합
- UI git 매칭 (집찾봇 브랜드, 카카오 버튼, 비밀번호찾기)
- 회원가입/로그인 (이메일+비번, JWT, bcrypt 직접 사용)
- DB 통합 (sqlite3 + DBeaver)
- **청년정책 흐름 연결**: JWT 나이/성별 + 챗봇 5개 슬롯(취업·소득·혼인·학력·무주택) → youth_policy_module 실 데이터 연결. 하드코딩 더미 완전 제거.
- **소소한 대화(small talk) 지원**: 안녕·감사·도움·재시작·잡담 등 자연어 인사 처리. 슬롯 3개 이상 채워진 상태에서는 자동 비활성화.
- **청년정책 흐름 개편 1단계**: 회원가입 폼에 취업상태(3종)·학력(4종) 라디오 버튼 추가. JWT에 employment/education 포함. bot.user_meta에 두 필드 주입.

**🔄 권장 추가 작업 (시간 여유 시)**
- **회원가입 설계 메모 권장사항 반영**:
  - 개인정보 수집·이용 동의 체크박스 (법적 권고)
  - 비밀번호 영문+숫자 조합 검증 강화 (현재 8자만 체크)
- 카카오 OAuth 키 발급 + `.env`에 `KAKAO_CLIENT_ID`/`KAKAO_CLIENT_SECRET` 추가
- Gmail SMTP 설정 (비밀번호찾기 실제 발송) — 앱 비밀번호 발급 필요
- Phase 5: vibe 학술 근거 자료 정리 (web search 기반)
- 폴더 구조 재정리 (`docs/`, `core/`, `chatbot/`, `data/`, `tests/`)

**🚀 마감 전 MUST**
- 모바일 반응형 검증 (실기기/DevTools)
- 추천 결과 UI 마무리 (지도뷰 등 disabled 메뉴 처리 확인)
- 외부 시연 준비 (Cloudflare Tunnel)



---

## 12. 메모 갱신 양식 (Claude Code & 사용자용)

이 메모는 **작업 단위가 끝날 때마다 갱신**한다. 갱신 책임은 다음과 같다:

- **Claude Code**: 한 작업 단위(수정/기능 추가/디버깅 세트)가 끝나면 사용자에게 보고하면서 이 메모의 해당 섹션을 같이 갱신.
- **사용자**: Claude.ai 또는 다른 환경에서 작업한 내용은 직접 추가하거나 Claude Code에게 "이 내용 인수인계 메모에 추가해줘" 요청.

### 12-1. 갱신 시점

다음 상황 중 하나라도 해당되면 갱신:

- 새 기능을 구현하거나 버그를 고쳤을 때
- 설계 결정이 바뀌었을 때 (예: API 교체, 라이브러리 변경)
- 새 환경 설정/의존성이 추가됐을 때
- 알려진 함정/주의사항이 새로 생겼을 때
- 작업 흐름이나 결정된 정책이 추가/변경됐을 때

### 12-2. 갱신 양식 — 새 작업 항목 추가

**섹션 2 (완료된 작업 이력)**에 다음 양식으로 추가:

```
### [작업명] (날짜)
- 파일명: 변경 내용 한 줄 요약
- 파일명: 변경 내용 한 줄 요약
결과: 정상 동작 확인 / 미확인
```

### 12-3. git 커밋 규칙
- 작업 단위 완료 후 커밋
- 메시지 형식: `fix: [내용]` / `feat: [내용]` / `refactor: [내용]`
- `.env` 절대 커밋하지 말 것 (`.gitignore` 확인)