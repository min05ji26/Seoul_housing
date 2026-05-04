# Claude Code 인수인계 메모
작성일: 2026-05-04 (최종 갱신)
이전 환경: Claude.ai (서울살이 v5 프로젝트)
다음 환경: Claude Code

---

## 0. 즉시 해야 할 일 (Claude Code 첫 명령)

새 Claude Code 세션 시작 후 다음을 먼저 실행하라고 지시:

1. `Claude_Code_작업지시.md` 읽기 (워크플로우 + 작업 우선순위)
2. 이 메모(`Claude_Code_인수인계.md`) 읽기
3. `프로젝트_변경_계획.md` 읽기
4. `housing_recommendation_v5.py` 읽기 (파일명 변경됨: `__1_` 없음)
5. **다음 작업: Phase 2 (혼잡계수/CSV 5개 제거)** — §3 참고

## [2026-05-04] 완료된 작업

- **환경변수 분리 완료**: API 키 6개 → `.env` 파일로 분리 (Git 제외)
- **노트북 경로 교체 완료**: `kj77k` → `JangKyoungJun` (housing_recommendation_v5.py, feedback_module.py)
- **백업 생성**: `*_backup.py` 3개 (gitignore 제외)
- **Git repo 신규 생성**: `https://github.com/kj77kj7/housing_recommendation.git`
- **Phase 1 baseline 검증**: scenario1~4 정상 (데스크톱에서 2026-05-03 완료)
- **Phase 2 완료 + 검증 완료**: 혼잡계수/CSV 5개 제거 (-222줄, 시나리오1 실행 검증)
  - 제거: 정적 파일 경로 5개, 혼잡계수 테이블 3개+함수 3개, CSV 로드 함수 5개, lookup 빌드 함수 5개, calculate_adjusted_transit_time 함수
  - 단순화: calc_commute_both_ways (파라미터 5개 제거, ODsay pathTime 직접 사용)
  - 추가 수정: 데이터 한계 안내에서 "혼잡계수: TOPIS 통계 기반" 문구 제거 (Phase 2에서 폐지된 기능)
  - 검증 결과: ODsay IP 등록 후 시나리오1 정상 완료 (성동구 3개 매물 추천, 최단 11분)
- **Phase 3 완료**: 자가용 API v1/directions → v1/future/directions 전환
  - `_next_weekday_at()` 헬퍼 추가 (출발 시각 → YYYYMMDDHHMM 변환)
  - `get_drive_route_kakaomobility()`: departure_time 파라미터 추가, future/directions 분기
  - `calc_commute_both_ways()`: 출근/퇴근 시각을 각각 departure_time으로 전달
  - **다음 작업: Phase 4 (자가용 시나리오 재검증)**
- **Phase 4 완료**: 시나리오 1(대중교통) + 시나리오 2(자가용) 검증 이상 없음
  - 자가용: 송파구 200개 매물, future/directions API 출근/퇴근 시각 별도 계산 정상
  - 대중교통: ODsay 정상
  - **다음 작업: Phase 5 (vibe 측정 근거 정리) — PC에서 진행 예정**

## API 키 설정 (신규 PC 작업 시 필수)

- `.env` 파일은 Git에 없음 (보안상 제외)
- 새 PC에서 작업 시작 시: `.env` 파일을 별도로 받아서 프로젝트 루트에 위치
- `.env` 전송: USB / 메신저 직접 전송 / 비밀번호 관리자
- `.env.example` 파일에 키 목록 있음 (값은 비워져 있음)

## 향후 작업 항목 (메모)

- **경로 PC별 차이 문제**: `_DATA_DIR`, `SAVE_DIR`, `FEEDBACK_CSV_DIR`이 절대경로 하드코딩됨.
  git pull 시마다 경로 충돌 가능. 향후 (A) `.env`에 `PROJECT_ROOT` 추가 또는 (B) `__file__` 기준 상대경로 리팩토링 필요.

---

---

## 1. 프로젝트 한 줄 요약

**서울살이 v5** — 서울 거주지 추천 시스템. 2026 서울시 빅데이터 활용 경진대회 창업부문 출품 예정 (마감 5/13).

3축 Fuzzy TOPSIS (통근 + 주거비 + 인프라) + 청년정책 통합. 3단계 계층적 필터링 (구 → 동 → 매물).

---

## 2. 현재까지의 핵심 결정 사항

### 교통 데이터 처리 (확정)
- 자가용: 카카오모빌리티 **future/directions API**로 전환 (시간대별 혼잡 자동 반영)
- 대중교통: **ODsay 그대로**, 혼잡도 보정 일체 없음
- 혼잡계수 테이블 3개(CAR/BUS/SUBWAY) 모두 **제거**

### 정적 파일 (확정)
- **유지: 1개** — `주거비_데이터_최종통합버전.csv` (97MB, 597,797건)
  - 1·2단계 자치구·동 단위 시세 분포 통계 산출용
  - 갱신 주기: **반기 1회**
  - 즉시 작업: 2025-01부터 현재까지 데이터 추가 수집 필요
- **제거: 5개**
  - 지하철_배차간격_데이터.csv
  - 버스도착정보_통합.csv
  - 서울교통공사_역별요일별환승인원_통합.csv
  - 서울교통공사_환승역거리_소요시간_20250310.csv
  - 서울시버스노선기본정보_통합본.xlsx

### AI 기능 통합 방향 (확정)
1. 자연어 입력 챗봇 (LLM 슬롯 추출 → JSON → v5 파라미터)
2. vibe 카테고리 매핑 (학술 근거 기반: POI 밀도 + 다양성 + 생활인구)
3. 청년정책 LLM 요약 (메모 §AI 통합 참고)

### 챗봇 슬롯 정의 (확정)
- **필수 슬롯 5개**: 직장주소, 이동수단, 예산, 통근시간, 주택유형
- **선택 슬롯**: 지역, 우선순위, 출퇴근시각, vibe, 청년정책

### UI 프레임워크 (확정)
- **Streamlit** (Python 단일 파일로 웹 UI)
- 향후 모바일 앱 전환 가능성 있음

### LLM 호출 (보류)
- 설계 단계에서는 더미 함수로 진행
- 실제 LLM은 나중에 연결 (Anthropic Max 플랜은 직접 통합 불가, Gemini 무료 또는 별도 API 키 발급 예정)

---

## 3. 작업 우선순위 (이 순서대로 진행)

### Phase 1: Baseline 검증 (먼저 해야 함)
변경 전에 현재 v5가 정상 작동하는지 확인.

```bash
cd /path/to/project
python housing_recommendation_v5__1_.py
# 또는 IDLE에서 실행
```

검증 포인트:
- [ ] 모든 API 키 유효 (KAKAO_REST_API_KEY, KAKAO_MOBILITY_API_KEY, ODSAY_API_KEY, MOLIT_API_KEY, ONTONG_API_KEY)
- [ ] 정적 파일 6개 모두 로드 정상
- [ ] 주거비 CSV (97MB) 로드 정상
- [ ] 1단계 (구 필터링) 정상 출력
- [ ] 2단계 (동 필터링) 정상 출력
- [ ] 3단계 (매물 추천) 정상 출력
- [ ] 청년정책 모듈 동작 정상

### Phase 2: 변경 계획 적용 (제거 작업)

**제거할 코드 영역 (housing_recommendation_v5__1_.py):**

#### 2-1. 정적 파일 경로 상수 4개 제거 (line 24~27)
```
SUBWAY_HEADWAY_CSV
BUS_ARRIVAL_CSV
SUBWAY_TRANSFER_LOAD_CSV
SUBWAY_TRANSFER_TIME_CSV
```
(BUS_HEADWAY_XLSX도 있으면 같이 제거)

#### 2-2. 혼잡계수 테이블/함수 제거 (line 76~125)
```
BUS_CONGESTION_PENALTY (line 76)
CAR_CONGESTION_BY_HOUR (line 87)
BUS_CONGESTION_BY_HOUR (line 104)
SUBWAY_CONGESTION_BY_HOUR (line 109)
get_car_coeff() (line 115)
get_bus_coeff() (line 119)
get_subway_coeff() (line 123)
```

#### 2-3. CSV 로드 함수 5개 제거 (line 796~825 부근)
```
load_subway_headway()
load_bus_arrival()
load_subway_transfer_load()
load_subway_transfer_time()
load_bus_route_base()
```

#### 2-4. 빌드 lookup 함수들 제거 (line 827~870 부근)
```
build_subway_wait_lookup()
build_bus_stop_lookup()
build_subway_load_lookup()
build_bus_route_headway_lookup()
```

#### 2-5. transit 분기 보정 로직 제거 (line 900~1100 부근)
- `run_transit_route_with_features()` 함수 시그니처 단순화
- `sw_wait`, `sw_load`, `tr_time`, `bus_stop`, `bus_route_hw` 파라미터 모두 제거
- 환승 대기/혼잡 보정 코드 제거
- ODsay 결과(`pathTime`) 그대로 반환하도록 단순화

#### 2-6. main 흐름의 lookup 빌드 부분 제거 (line 1577 부근)
```python
sw_wait = sw_load = tr_time = bus_stop = bus_route_hw = None
if transport_mode == "transit":
    sw_wait = build_subway_wait_lookup(load_subway_headway(SUBWAY_HEADWAY_CSV))
    bus_stop = build_bus_stop_lookup(load_bus_arrival(BUS_ARRIVAL_CSV))
    sw_load = build_subway_load_lookup(load_subway_transfer_load(SUBWAY_TRANSFER_LOAD_CSV))
    # ...
```
이 블록 전체 제거.

### Phase 3: 카카오 future/directions API 전환

#### 3-1. 자가용 호출 함수 변경
- 기존 Directions API → future/directions API
- 엔드포인트: `https://apis-navi.kakaomobility.com/v1/future/directions`
- 파라미터에 `departure_time=YYYYMMDDHHMM` 추가

#### 3-2. 출발 시각 datetime 변환 헬퍼 추가
```python
def next_weekday_at(hour, minute):
    """현재 시각 기준 다음 평일 hh:mm의 datetime 반환"""
    # 현재 시각이 시연 새벽이든 저녁이든 항상 일관된 평일 결과
```

#### 3-3. 자가용 분기에서 혼잡계수 곱셈 제거
- future API 응답의 `duration` 그대로 사용
- 곱셈 보정 코드 모두 삭제

### Phase 4: 변경 후 baseline 재검증

Phase 1과 동일한 검증을 변경 후 코드로 수행.

### Phase 5: vibe 측정 근거 정리 메모 작성

**목적**: "우리가 이렇게 정했다"가 아닌 "이 자료에서 이렇게 측정했기 때문" 이라고 발표에서 말할 수 있게 하는 것.

**진행 방식**:
1. 웹 검색으로 공신력 있는 자료 수집
   - 학술 논문 (KCI, arXiv, Google Scholar)
   - 공공기관 보고서 (서울연구원, 국토연구원 등)
   - 참고 키워드: Jacobs 도시활력, 서울시 POI 빅데이터, 15분 도시, Liveability Index, 생활인구
2. 찾은 자료에서 vibe 5개 카테고리(번화함/조용함/청년활기/가족친화/자연친화) 측정 지표를 뒷받침하는 내용 추출
3. `vibe_학술근거.md` 작성
   - 각 vibe별: 측정 지표 + 근거 자료 출처 + 왜 이 지표인지 한 줄 설명
   - v5 적용 시 사용할 실제 측정 방식 표로 정리

### Phase 6: Streamlit + 챗봇 개발

#### 6-1. nlp_input_module.py 신규 작성
- 더미 슬롯 추출기 (정규식 기반)
- 챗봇 상태 머신 (한 번에 1개씩 역질문)
- 무한 루프 방지 장치 (MAX_TURNS=7, MAX_SAME_QUESTION=2)

#### 6-2. vibe_module.py 신규 작성
- POI 밀도 + 다양성 계산
- vibe 카테고리 → 인프라 가중치 매핑

#### 6-3. streamlit_app.py 신규 작성
- 좌측: 챗봇 대화창
- 우측: 슬롯 추출 상태 + 추천 결과
- 디버깅 패널: 각 단계 데이터 실시간 표시

---

## 4. 슬롯 스키마 (확정 직전 상태)

```python
SLOT_SCHEMA = {
    # 필수 5개
    "work_address": str,           # 직장 주소
    "transport_mode": str,         # "car" | "transit"
    "budget": {                    # 예산
        "rent_type": str,          # "전세" | "월세"
        "deposit_manwon": int,
        "monthly_manwon": int,     # 전세 시 None
    },
    "allowed_minutes": int,        # 허용 통근시간
    "house_type": str,             # "연립다세대" | "오피스텔"
    
    # 선택 슬롯
    "region_filter": str,          # 지역 (예: "강남구")
    "weight_preference": str,      # "통근우선" | "주거비우선" | "균형"
    "depart_time": str,            # "HHMM"
    "arrive_time": str,            # "HHMM"
    "vibe": str,                   # 5개 카테고리 중 1
    "use_youth_policy": bool,
}
```

---

## 5. vibe 카테고리 (학술 근거 기반)

5개 카테고리 + 측정 지표:

| vibe | 측정 지표 | 데이터 출처 |
|---|---|---|
| 번화함 | POI 밀도 상위 + 생활인구 상위 | 카카오 + 서울 생활인구 |
| 조용함 | POI 밀도 하위 + 생활인구 하위 | 카카오 + 서울 생활인구 |
| 청년활기 | 카페·헬스장 POI 비중 + 20대 비중 | 카카오 + 인구통계 |
| 가족친화 | 학교·병원·약국 POI 비중 + 30~40대+영유아 비중 | 카카오 + 인구통계 |
| 자연친화 | 공원 POI 거리 + 녹지율 | 카카오 + 도시계획 데이터 |

→ 마감 안에 풀세팅 어려우면 **POI 밀도만** 사용한 단순화 버전으로 시작 가능.

---

## 6. 기존 산출 파일 위치

`/mnt/user-data/outputs/` 또는 프로젝트 폴더:
- `프로젝트_변경_계획.md` (변경 계획 결정 + 학술 근거)
- `주거비_데이터_정보_메모.md` (데이터 구조)

---

## 7. 주의사항 & 함정

### 주의 1: 사용자 작업 스타일
- "내가 묻기 전엔 먼저 묻지 말 것"
- "방향 결정 전 무작정 코드부터 올리지 말 것"
- "답변이 너무 길면 안 됨" — 핵심만 짚어서 짧게
- "답변 불가능 상황에서 토큰 낭비하지 말 것"

### 주의 2: API 키 보안
- v5 코드 line 12~17 부근에 API 키 직접 하드코딩되어 있음
- Streamlit 배포 시 절대 GitHub 등에 노출 금지
- 환경변수로 분리 권장

### 주의 3: 절대 경로
- v5 코드의 파일 경로가 Windows 절대 경로 (`C:\Users\JangKyoungJun\Downloads\...`)
- 다른 PC에서 실행하려면 상대 경로로 변경 필요

### 주의 4: 메모리 부담
- 주거비 CSV 97MB, 597,797행 로드
- Streamlit 매번 재로드하면 느림 → `@st.cache_data` 데코레이터 필수

### 주의 5: 카카오 future/directions API
- 기존 Directions API와 엔드포인트가 다름
- `departure_time` 파라미터 형식: `YYYYMMDDHHMM` (12자리, 분 단위)
- 응답 형식은 거의 동일하나 `traffic_state`, `traffic_speed` 필드 추가됨

---

## 8. 마감 일정

- 경진대회 접수 마감: **2026-05-13 18:00** (남은 기간 약 1.5주)
- 1차 결과 발표: 2026-05-22

### 권장 우선순위 (마감 우선)
1. **MUST**: Phase 1~4 (코드 정상화, 필수)
2. **MUST**: Phase 6-1, 6-3 (챗봇 + Streamlit, 발표 핵심)
3. **SHOULD**: Phase 6-2 (vibe 단순화 버전)
4. **NICE**: 학술 근거 메모 (발표 보조 자료)
5. **DROP**: vibe 풀세팅 (생활인구 API 통합)은 마감 후로

---

## 9. 사용자가 좋아하는 작업 흐름

1. 결정 필요한 사항 명확히 제시 → 사용자 결정 → 다음 단계
2. 코드 변경은 "어디를 어떻게" 먼저 설명 → 동의 후 적용
3. 각 단계 완료 후 사용자가 직접 검증 가능하게 break point 만들기
4. 학술 근거나 신뢰성 있는 자료가 필요하면 web search로 검증

---

## 10. 다음 행동

Claude Code 새 세션에서:
1. 이 메모 읽었음을 확인
2. 프로젝트 폴더 구조 파악
3. Phase 1 baseline 검증 시작 — 사용자에게 v5 직접 실행 요청
4. 결과 확인 후 Phase 2 진행 여부 사용자에게 확인
