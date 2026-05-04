# Claude Code 작업 지시 (서울살이 v5 — 환경변수 분리 + Phase 2 + Git 워크플로우 도입)

작성일: 2026-05-04
대상: Claude Code 새 세션
이번 작업 위치: **노트북** (이번 세션은 노트북에서 진행)

---

## 0. 작업 환경 정보 (양쪽 PC)

이 프로젝트는 데스크톱과 노트북을 왕복하며 작업합니다. 양쪽 정보를 모두 적어둡니다.

### 데스크톱
- 사용자명: `kj77k`
- 프로젝트 경로: `C:\Users\kj77k\Downloads\서울살이_프로젝트`
- Python: 3.10
- 데이터 경로: `C:\Users\kj77k\Downloads\서울살이_프로젝트\사용_csv_모음`
- 결과 경로: `C:\Users\kj77k\Downloads\서울살이_프로젝트\api코드결과`

### 노트북 (이번 세션)
- 사용자명: `JangKyoungJun`
- 프로젝트 경로: `C:\Users\JangKyoungJun\Downloads\서울살이_프로젝트`
- Python: 3.9 (IDLE)
- 데이터 경로: `C:\Users\JangKyoungJun\Downloads\서울살이_프로젝트\사용_csv_모음`
- 결과 경로: `C:\Users\JangKyoungJun\Downloads\서울살이_프로젝트\api코드결과`

### PC 판별 방법 (Claude Code가 작업 시작 시 확인)
파일 시스템에서 현재 경로를 확인해 어느 PC인지 자동 판별:
- 경로에 `kj77k` 포함 → 데스크톱
- 경로에 `JangKyoungJun` 포함 → 노트북

---

## 1. 새 워크플로우 (Git 도입 후)

### 1-1. 변경 전 (지금까지)
- 코드 수정 → 폴더 통째로 zip → 다른 PC로 옮김
- 인수인계 정보가 코드와 함께 zip 안에 있음

### 1-2. 변경 후 (이번 작업으로 도입)
- **코드 동기화는 Git이 담당** (commit / push / pull)
- **작업 맥락 동기화는 `Claude_Code_인수인계.md`가 담당** (Git에 함께 올라감)
- API 키는 `.env` 파일에 분리 → `.gitignore`로 Git 추적 제외 → 두 PC 각각 로컬에 .env 별도 보관

### 1-3. 매 작업 시 표준 흐름

**작업 시작 시:**
```
1. git pull                        ← 다른 PC 변경사항 가져오기
2. Claude_Code_인수인계.md 읽기    ← 어디까지 했는지 확인
3. 작업 시작
```

**작업 중 (각 단계 완료 시):**
```
1. 코드 변경 적용
2. Claude_Code_인수인계.md 즉시 갱신 (현재 단계, 다음 행동, 결정 사항)
3. 사용자에게 검증 요청 (필요 시)
```

**세션 종료 시 (반드시):**
```
1. Claude_Code_인수인계.md 최종 점검
2. 사용자에게 git commit + push 안내
   예: git add .
       git commit -m "Phase 2 완료: 혼잡계수/CSV 5개 제거"
       git push
3. 다음 PC에서 git pull로 이어갈 수 있음을 사용자에게 상기
```

### 1-4. 인수인계 md 갱신 = 필수
- 인수인계 파일 갱신은 **선택이 아니라 필수**
- 갱신 없이 세션 종료 금지
- 갱신 없이 git push 금지 (코드만 올라가면 다른 PC에서 작업 맥락을 모름)

---

## 2. 작업 시작 전 필수 확인

다음 파일들을 **순서대로** 먼저 읽으세요:
1. `Claude_Code_인수인계.md` — 프로젝트 전체 맥락
2. `프로젝트_변경_계획.md` — Phase 2~3 변경 근거
3. `housing_recommendation_v5.py` — 메인 코드
4. `youth_policy_module.py` — 청년정책 모듈
5. `job_search_module.py` — 채용공고 모듈

---

## 3. 작업 컨텍스트 (현재 상태)

- **Phase 1 baseline 검증 완료**: scenario1~4 모두 정상 종료 (2026-05-03 19:18~20:34, 데스크톱에서 진행)
- **다음 작업**: 환경변수 분리(신규) → 노트북 경로 교체 → Phase 2 (혼잡계수/CSV 5개 제거)
- **마감**: 2026-05-13 18:00 (서울시 빅데이터 활용 경진대회)
- **Git 도입**: 이번 세션 작업 후 첫 commit 예정

---

## 4. 작업 지침 — 매우 중요

### 4-1. 작업 흐름 원칙
- **각 단계 완료 후 사용자에게 확인 요청** — 무작정 다음 단계로 넘어가지 말 것
- 코드 변경 전에 **어디를 어떻게** 먼저 설명 → 사용자 동의 후 적용
- 답변이 너무 길면 안 됨 — 핵심만 짧게
- 답변 불가능 상황에서 **토큰 낭비 금지** (작업 멈추고 이유 설명)

### 4-2. 사용자 작업 스타일 (반드시 준수)
- 내가 묻기 전엔 먼저 묻지 말 것
- 방향 결정 전 무작정 코드부터 올리지 말 것
- 답변이 너무 길면 안 됨 — 핵심만 짧게
- 각 단계 완료 후 사용자가 직접 검증 가능하게 break point 만들기
- 학술 근거나 신뢰성 있는 자료가 필요하면 web search로 검증

---

## 5. 환경변수 분리 작업 (먼저 진행)

### 5-1. 배경
- 노트북-데스크톱 간 Git으로 코드 동기화 예정
- API 키는 `.env` 파일로 분리 후 `.gitignore`에 추가 → Git에 안 올라감
- 다른 PC에서는 `.env` 파일만 별도로 받아서 프로젝트 루트에 두면 동작

### 5-2. 분리 대상 API 키 (총 6개)

| # | 파일 | 라인 | 변수명 |
|---|---|---|---|
| 1 | housing_recommendation_v5.py | 37 | KAKAO_LOCAL_REST_API_KEY |
| 2 | housing_recommendation_v5.py | 38 | KAKAO_MOBILITY_REST_API_KEY |
| 3 | housing_recommendation_v5.py | 39 | ODSAY_API_KEY |
| 4 | housing_recommendation_v5.py | 40 | MOLIT_API_KEY |
| 5 | youth_policy_module.py | 23 | YOUTH_API_KEY |
| 6 | job_search_module.py | 20 | SEOUL_JOB_API_KEY |

### 5-3. 작업 단계

**Step 1: 백업 생성**
```
housing_recommendation_v5.py → housing_recommendation_v5_backup.py
youth_policy_module.py → youth_policy_module_backup.py
job_search_module.py → job_search_module_backup.py
```

**Step 2: python-dotenv 설치 안내**
사용자에게 다음 명령 실행 요청:
- 노트북(Python 3.9): `py -3.9 -m pip install python-dotenv` 또는 `pip install python-dotenv`
- 데스크톱(Python 3.10): `py -3.10 -m pip install python-dotenv` 또는 `pip install python-dotenv`

**Step 3: `.env` 파일 생성** (프로젝트 루트)

기존 코드에서 다음 키 값들을 추출해서 `.env` 파일에 그대로 옮기기:
- housing_recommendation_v5.py line 37~40 의 KAKAO_LOCAL_REST_API_KEY, KAKAO_MOBILITY_REST_API_KEY, ODSAY_API_KEY, MOLIT_API_KEY 값
- youth_policy_module.py line 23 의 YOUTH_API_KEY 값
- job_search_module.py line 20 의 SEOUL_JOB_API_KEY 값

`.env` 파일 형식:
```
KAKAO_LOCAL_REST_API_KEY=(원본 코드에서 추출한 값)
KAKAO_MOBILITY_REST_API_KEY=(원본 코드에서 추출한 값)
ODSAY_API_KEY=(원본 코드에서 추출한 값)
MOLIT_API_KEY=(원본 코드에서 추출한 값)
YOUTH_API_KEY=(원본 코드에서 추출한 값)
SEOUL_JOB_API_KEY=(원본 코드에서 추출한 값)
```

주의: 값에 따옴표 붙이지 말 것. `KEY=값` 형식 그대로.

**Step 4: `.env.example` 파일 생성** (Git에 올라감, 키 값은 비워둠)
```
# 서울살이 v5 API 키 — 실제 값은 .env 파일에 입력
KAKAO_LOCAL_REST_API_KEY=
KAKAO_MOBILITY_REST_API_KEY=
ODSAY_API_KEY=
MOLIT_API_KEY=
YOUTH_API_KEY=
SEOUL_JOB_API_KEY=
```

**Step 5: `.gitignore` 파일 생성/업데이트** (프로젝트 루트)
```
# 환경변수 (API 키)
.env

# Python
__pycache__/
*.pyc
*.pyo

# IDE
.vscode/
.idea/

# 결과물
api코드결과/

# 백업
*_backup.py

# 데이터 (용량 큼, 별도 관리)
사용_csv_모음/
```

**Step 6: 코드 수정**

`housing_recommendation_v5.py` 상단 (import 영역, line 1~9 사이):
```python
import os
# ... 기존 import 들 ...

from dotenv import load_dotenv
load_dotenv()
```

API 키 영역 (line 34~40) 교체:
```python
# =========================================================
# 2. API 키 (.env 파일에서 로드)
# =========================================================
KAKAO_LOCAL_REST_API_KEY    = os.getenv("KAKAO_LOCAL_REST_API_KEY")
KAKAO_MOBILITY_REST_API_KEY = os.getenv("KAKAO_MOBILITY_REST_API_KEY")
ODSAY_API_KEY               = os.getenv("ODSAY_API_KEY")
MOLIT_API_KEY               = os.getenv("MOLIT_API_KEY")

# 키 누락 검증
_missing_keys = [k for k, v in {
    "KAKAO_LOCAL_REST_API_KEY": KAKAO_LOCAL_REST_API_KEY,
    "KAKAO_MOBILITY_REST_API_KEY": KAKAO_MOBILITY_REST_API_KEY,
    "ODSAY_API_KEY": ODSAY_API_KEY,
    "MOLIT_API_KEY": MOLIT_API_KEY,
}.items() if not v]
if _missing_keys:
    raise RuntimeError(f"[.env] 누락된 API 키: {', '.join(_missing_keys)}")
```

`youth_policy_module.py`:
- 파일 상단 import 영역에 `os` import 없으면 추가, `from dotenv import load_dotenv` + `load_dotenv()` 추가
- line 23 수정: `YOUTH_API_KEY = os.getenv("YOUTH_API_KEY", "")`

`job_search_module.py`:
- 파일 상단 import 영역에 `import os`, `from dotenv import load_dotenv`, `load_dotenv()` 추가
- line 20 수정: `SEOUL_JOB_API_KEY = os.getenv("SEOUL_JOB_API_KEY", "")`

**Step 7: 절대 경로 처리 — 현재 PC 경로로 교체**

코드 안의 모든 `kj77k` 또는 `JangKyoungJun` 절대 경로를 **현재 작업 중인 PC 경로**로 교체.

이번 세션은 노트북에서 진행하므로:
- `C:\Users\kj77k\...` → `C:\Users\JangKyoungJun\...` 로 교체

`housing_recommendation_v5.py`:
- line 23: `_DATA_DIR = r"C:\Users\kj77k\Downloads\서울살이_프로젝트\사용_csv_모음"` → 노트북 경로로 교체
- line 30: `SAVE_DIR = r"C:\Users\kj77k\Downloads\서울살이_프로젝트\api코드결과"` → 노트북 경로로 교체

추가 검토: 다른 파일에도 절대 경로가 있는지 grep으로 확인하고 같이 수정.

**경로 처리 관련 향후 개선 (지금은 보류, 인수인계에 메모)**:
양쪽 PC 사용자명이 달라서 git pull 시마다 경로 충돌 발생 가능. 본격적인 해결책 두 가지:
- (A) 환경변수로 경로 처리 (`.env`에 `PROJECT_ROOT` 추가)
- (B) `__file__` 기준 상대 경로로 리팩토링

이번 세션은 빠르게 노트북 경로로만 교체하고, 본격적인 해결은 별도 작업으로 진행. **인수인계 파일에 "경로 PC별 차이 문제"를 향후 작업 항목으로 기록할 것.**

**Step 8: scenario1 검증**
- 사용자에게 v5 직접 실행 요청 (IDLE 또는 명령 프롬프트)
- scenario1만 빠르게 돌려서 환경변수 로드 + 노트북 경로 정상 작동 확인
- 정상 작동 확인 후 Phase 2 진입

---

## 6. Phase 2 작업 — 혼잡계수/CSV 제거

(환경변수 분리 + scenario1 검증 통과 후 진행)

### 6-1. 제거 대상 (실제 라인 번호 기준, 환경변수 분리 후 라인 번호 약간 밀림 주의)

| # | 영역 | 원본 라인 | 내용 |
|---|---|---|---|
| 1 | 정적 파일 경로 5개 | 25~29 | SUBWAY_HEADWAY_CSV, BUS_ARRIVAL_CSV, SUBWAY_TRANSFER_LOAD_CSV, SUBWAY_TRANSFER_TIME_CSV, BUS_ROUTE_BASE_XLSX (HOUSING_CSV_PATH는 유지) |
| 2 | BUS_CONGESTION_PENALTY | 77 | (참고: build_bus_route_headway_lookup 안에서만 사용, 함수가 #4에서 제거되니 함께 정리) |
| 3 | 혼잡계수 테이블/함수 | 80~125 | 섹션 헤더(80~87) + CAR/BUS/SUBWAY 딕셔너리 3개(88~113) + coeff 함수 3개(116~125) |
| 4 | CSV 로드 함수 5개 | 797~826 | load_subway_headway, load_bus_arrival, load_subway_transfer_load, load_subway_transfer_time, load_bus_route_base |
| 5 | 빌드 lookup 함수 5개 | 828~870 부근 | build_subway_wait_lookup, build_bus_stop_lookup, build_subway_load_lookup, build_transfer_time_lookup, build_bus_route_headway_lookup |
| 6 | run_transit_route_with_features 시그니처 단순화 | 901~ | sw_wait/sw_load/tr_time/bus_stop/bus_route_hw 5개 파라미터 제거, 환승 대기/혼잡 보정 로직 제거, ODsay pathTime 그대로 반환 |
| 7 | calc_commute_both_ways 보정 | 945~1064 | transit 분기의 sw_wait...bus_route_hw 파라미터 제거. **자가용 분기는 Phase 3에서 future API로 일괄 교체할 것이므로 Phase 2에서는 손대지 말 것**. car_coeff_am/pm 출력 필드도 Phase 3에서 정리 |
| 8 | main 흐름 lookup 빌드 | 1577~1584 | `sw_wait = sw_load = tr_time = bus_stop = bus_route_hw = None`부터 `if transport_mode == "transit":` 블록 전체 제거 |
| 9 | calc_commute_both_ways 호출부 | 1708~1712 | `sw_wait, sw_load, tr_time, bus_stop, bus_route_hw,` 인자 제거 |

### 6-2. 작업 순서
1. 위 표 #1부터 순서대로 한 영역씩 수정
2. 각 영역 작업 후 라인 번호가 밀리므로, **다음 영역 들어가기 전 코드 재확인**
3. 모든 작업 끝나면 `python -m py_compile housing_recommendation_v5.py`로 문법 검증
4. 변경 전후 라인 수 비교 보고 (대략 -150~200 라인 예상)
5. **Phase 2 완료 후 사용자에게 baseline 재검증 요청** — scenario 1~4 정상 작동 확인

### 6-3. Phase 2에서 의도적으로 손대지 않을 부분
- **자가용(car) 분기 혼잡계수 곱셈** (line 957~959, 968~969): Phase 3에서 future API로 일괄 교체 예정
- **car_coeff_am / car_coeff_pm 출력 필드** (line 979~980): Phase 3에서 같이 정리

이유: Phase 2 변경 후 검증 시 자가용 결과가 깨지면 Phase 3과 섞여서 디버깅이 어려움.

---

## 7. 이번 세션 작업 우선순위

순서대로:

1. **백업 생성** (3개 파일)
2. **python-dotenv 설치** (사용자 직접)
3. **환경변수 분리** — .env, .env.example, .gitignore 생성 + 3개 파일 코드 수정
4. **노트북 경로로 수정** — _DATA_DIR, SAVE_DIR 경로 교체
5. **scenario1 검증** — 환경변수 + 노트북 경로 정상 동작 확인
6. **Phase 2 코드 제거 작업** — §6-1 표 순서대로
7. **Phase 2 최종 검증** — scenario1~4 사용자 직접 실행
8. **인수인계 파일 갱신** — Phase 2 완료 + 다음 행동 = "Phase 3" + 경로 PC별 차이 문제 기록
9. **Git 첫 commit + push 안내** — 사용자가 직접 진행

### Git 작업 안내 (세션 마지막에 사용자에게 전달)

세션이 끝나면 다음 명령 실행하시면 됩니다:
```
cd C:\Users\JangKyoungJun\Downloads\서울살이_프로젝트
git status                        # 변경 파일 확인 (.env가 안 보여야 정상)
git add .
git commit -m "환경변수 분리 + Phase 2 완료"
git push
```

데스크톱에서는:
```
cd C:\Users\kj77k\Downloads\서울살이_프로젝트
git pull
# .env 파일은 별도 보관본을 프로젝트 루트에 복사 (USB / 메신저 등으로 한 번만 옮기면 됨)
```

---

## 8. 다음 행동

Claude Code 첫 응답:
1. 이 지시문 읽었음 확인
2. `Claude_Code_인수인계.md` 읽고 현황 파악 보고
3. 현재 PC가 노트북(`JangKyoungJun`)인지 확인
4. 백업 생성 후 환경변수 분리부터 시작 의향 확인 요청
