# Phase 6-4 ~ 6-6 미실행 원인 및 수정 사항
작성일: 2026-05-05

---

## 현상

시나리오 3 실행 시 청년정책 섹션이 아래 메시지로만 종료됨:
```
[마포구] 주거비 절감에 도움되는 정책이 없습니다.
```
→ Phase 6-4(점수 산식), 6-5(중복 경고), 6-6(근거 출력 포맷) 코드가 전혀 실행되지 않음.

---

## 실행 조건 (코드 기준)

| Phase | 실행 조건 |
|---|---|
| **6-4** 점수 계산 | `policy_selection_flow()` 내 `verified` 리스트가 비어있지 않아야 함 |
| **6-5** 중복 경고 | 동일 조건 (`verified` 비어있지 않음) |
| **6-6** `print_policy_section()` | `housing_recommendation_v5.py` line 1352 — `policy_score > 0` AND `policy_matched` 리스트 존재 |

→ 세 Phase 모두 **candidates 리스트가 비어있으면 전혀 실행되지 않음.**

---

## 원인 1 — 온통청년 API 403 (페이지 제한)

### 증상
```
[온통청년 API 오류] HTTP 403
→ 전체 100건 조회 완료
```

### 원인
- `_fetch_all_policies(max_pages=5, page_size=50)` 에서 3페이지 이후 HTTP 403 반환
- 2페이지까지만 정상 수신 → 100건만 조회 (최대 250건 중)
- 주거 관련 마포구 정책이 3페이지 이후에 있을 경우 전혀 수신 안 됨

### 수정 방향
1. `SLEEP_BETWEEN` 을 `0.5` → `1.5` 이상으로 늘려 요청 간격 증가
2. 403 발생 시 재시도 로직 추가 (`_call_youth_api()` 내 retry with backoff)
3. 또는 API 콘솔에서 요청 한도/키 상태 확인

```python
# youth_policy_module.py 수정 예시
SLEEP_BETWEEN = 1.5  # 0.5 → 1.5

# _call_youth_api() 에 retry 추가
for attempt in range(3):
    resp = requests.get(...)
    if resp.status_code == 200:
        break
    time.sleep(2 ** attempt)  # 1, 2, 4초 backoff
```

---

## 원인 2 — 100건 중 마포구 주거 혜택 정책 0건

### 증상
100건 수신했지만 `_is_housing_related()` + `analyze_benefit() > 0` 를 통과하는 정책 없음

### 원인 추정
- 수신된 100건이 주거 카테고리 정책을 포함하지 않을 가능성
- `BENEFIT_PATTERNS` 정규식이 실제 API 응답 텍스트와 매칭되지 않을 가능성
- `_is_seoul_policy()` 의 `zipCd` 필터가 마포구 정책을 걸러낼 가능성

### 수정 방향 (디버깅)
```python
# _fetch_all_policies() 호출 후 임시 디버깅 코드 추가
all_p = _fetch_all_policies(max_pages=5, page_size=50)
housing_related = [p for p in all_p if _is_housing_related(p)]
print(f"전체 {len(all_p)}건 중 주거 관련: {len(housing_related)}건")
for p in housing_related[:3]:
    print(p.get("plcyNm"), p.get("lclsfNm"), p.get("zipCd", "")[:20])
```
→ 출력 결과 보고 `BENEFIT_PATTERNS` 정규식 보강 또는 `_is_housing_related()` 키워드 추가 필요

---

## 원인 3 — 테스트 시나리오 입력값이 정책 선택을 건너뜀

### 코드 위치
`test_v5_auto.py` 시나리오 3:
```python
"",   # 청년정책 선택 (건너뜀, 마포구)   ← 이 줄이 문제
"",   # 안전 여분 input
```

### 원인
`policy_selection_flow()` 내:
```python
sel_input = input(f"  선택: ").strip()
if not sel_input:
    print(f"  → 건너뜀 (정책 점수 미반영)")
    return 0.0, []    # ← 여기서 바로 반환, 6-4~6-6 실행 안 됨
```

### 수정 방향
후보 정책이 실제로 존재할 때 선택 번호 입력 필요:
```python
# test_v5_auto.py 시나리오 3 변경
"1",   # 정책 1번 선택
"y",   # 자격 조건 충족 확인
```
**단, 원인 1·2가 해결되어 candidates 리스트가 생긴 후에 변경해야 의미 있음.**

---

## 수정 우선순위

| 순서 | 작업 | 효과 |
|---|---|---|
| **1** | API 403 해결 (sleep 증가 + retry) | 전체 정책 수신 확보 |
| **2** | `_fetch_all_policies` 후 디버깅으로 주거 정책 수신 여부 확인 | 원인 2 진단 |
| **3** | 필요 시 `BENEFIT_PATTERNS` 또는 `HOUSING_DIRECT_KEYWORDS` 보강 | candidates 생성 확보 |
| **4** | 시나리오 3 입력값 변경 (`""` → `"1"`, `""` → `"y"`) | 6-4~6-6 실행 확인 |

---

## 단위 테스트 대안 (API 없이 6-4~6-6 확인)

API 문제 해결 전에 코드 자체를 검증하려면 mock 정책 데이터로 단위 테스트:
```python
mock_policy = {
    "plcyNm": "서울시 청년월세 지원",
    "plcySprtCn": "월 20만원 주거비 지원",
    "sprtTrgtMinAge": "19", "sprtTrgtMaxAge": "39",
    "lclsfNm": "주거",
    "_monthly_saving": 20.0,
    "_benefit_type": "월세보조",
    "_benefit_desc": "월 20만원 주거비 지원",
    "_is_housing": True,
    "_uncertain": False,
    "_saving_pct": 40.0,
}
score, verified = policy_selection_flow(
    [mock_policy], {"age": "27"}, "마포구",
    max_display=3, user_budget_monthly=40.0
)
```
