"""
vibe_module.py
──────────────
동네 분위기(vibe) 카테고리 → 인프라 가중치 변환 모듈

설계 근거 (vibe_매핑_설계.md):
  - Jacobs (1961) "The Death and Life of Great American Cities" — 도시활력 = 시설 다양성
  - 조월·이수기 (2021) "서울시 POI 빅데이터를 활용한 도시활력과 영향요인 분석" (KCI)
  - AHP-TOPSIS 결합 (Sustainability 2025 한국 주거단지 재개발 평가, 방법론 참고)
  - 가중치 1~5 척도는 1인 평가자 직관 기반. 향후 사용자 피드백 AHP 보정 예정.
  - 절대값보다 동네 간 상대 비교 용도로 사용.

흐름:
  자연어 입력 → extract_vibe_from_text() → vibe 카테고리 리스트
  → get_vibe_weights(vibe_list) → 인프라 7종 가중치 dict
  → v5 인프라 점수 가중 평균 적용
"""

from typing import List, Dict, Optional

# ──────────────────────────────────────────────────────────
# 인프라 7종 키 (housing_recommendation_v5.py INFRA_CATEGORY_MAP 순서와 일치)
# ──────────────────────────────────────────────────────────
INFRA_KEYS: List[str] = ["편의점", "병원", "약국", "마트", "카페", "헬스장", "공원"]

# ──────────────────────────────────────────────────────────
# vibe 8개 카테고리 (Claude_Code_인수인계_추가.md §1)
# ──────────────────────────────────────────────────────────
VIBE_CATEGORIES: List[str] = [
    "조용함", "번화함", "청년활기", "가족친화",
    "자연친화", "편의 우선", "운동·건강", "카페·문화",
]

# ──────────────────────────────────────────────────────────
# 원점수 표 (1~5 정수 척도, vibe_매핑_설계.md §6)
# 평가 기준: 1=매우 부적합, 5=매우 적합
# 순서: 편의점 / 병원 / 약국 / 마트 / 카페 / 헬스장 / 공원
# ──────────────────────────────────────────────────────────
VIBE_RAW_SCORES: Dict[str, Dict[str, int]] = {
    "조용함":   {"편의점": 3, "병원": 3, "약국": 3, "마트": 3, "카페": 1, "헬스장": 2, "공원": 5},
    "번화함":   {"편의점": 4, "병원": 2, "약국": 2, "마트": 3, "카페": 5, "헬스장": 4, "공원": 2},
    "청년활기": {"편의점": 4, "병원": 2, "약국": 2, "마트": 3, "카페": 5, "헬스장": 5, "공원": 3},
    "가족친화": {"편의점": 3, "병원": 5, "약국": 4, "마트": 5, "카페": 2, "헬스장": 3, "공원": 4},
    "자연친화": {"편의점": 3, "병원": 3, "약국": 3, "마트": 3, "카페": 2, "헬스장": 3, "공원": 5},
    "편의 우선": {"편의점": 5, "병원": 3, "약국": 3, "마트": 5, "카페": 3, "헬스장": 2, "공원": 2},
    "운동·건강": {"편의점": 3, "병원": 3, "약국": 3, "마트": 3, "카페": 2, "헬스장": 5, "공원": 5},
    "카페·문화": {"편의점": 3, "병원": 2, "약국": 2, "마트": 3, "카페": 5, "헬스장": 3, "공원": 3},
}

# ──────────────────────────────────────────────────────────
# 자연어 → vibe 카테고리 키워드 매핑 (정규식 폴백용)
# LLM 연결 후에는 이 키워드 대신 LLM 분류 결과 사용
# ──────────────────────────────────────────────────────────
_VIBE_KEYWORDS: Dict[str, List[str]] = {
    "조용함":    ["조용", "한적", "고즈넉", "사람 적", "차분", "평온", "조용한"],
    "번화함":    ["번화", "활기찬", "시끌", "사람 많", "떠들", "핫한", "번잡"],
    "청년활기":  ["젊은", "20대", "청년", "활기", "트렌디", "힙한"],
    "가족친화":  ["가족", "아이", "어린이", "육아", "안정적", "조용하고 안전"],
    "자연친화":  ["공원", "녹지", "산책", "자연", "숲", "강변", "하천"],
    "편의 우선": ["편의점", "마트", "생필품", "편리", "생활 편한", "장보기"],
    "운동·건강": ["헬스장", "헬스", "운동", "피트니스", "스포츠", "체육"],
    "카페·문화": ["카페", "커피", "디저트", "문화", "갤러리", "감성"],
}

# 매칭 불가 키워드 (재질문 유도용)
_UNRECOGNIZED_KEYWORDS: List[str] = [
    "역세권", "학세권", "신축", "치안", "안전", "재개발", "브랜드", "대형 평수",
]


# ──────────────────────────────────────────────────────────
# 핵심 함수
# ──────────────────────────────────────────────────────────

def normalize_weights(raw_dict: Dict[str, int]) -> Dict[str, float]:
    """
    1~5 원점수 dict → 합계=7 정규화 가중치 dict.

    정규화 공식: weight_i = score_i / sum(scores) * 7
    → 균등 배분(모두 동일 점수) 시 각 가중치 = 1.0
    → 점수 높을수록 해당 인프라에 가중치 집중
    """
    total = sum(raw_dict.values())
    n = len(raw_dict)  # 7
    return {k: round(v / total * n, 4) for k, v in raw_dict.items()}


def get_vibe_weights(vibe_list: Optional[List[str]]) -> Dict[str, float]:
    """
    vibe 카테고리 리스트 → 인프라 7종 가중치 dict 반환.

    - vibe_list가 None 또는 빈 리스트: 균등 가중치(1.0) 반환
    - 다중 vibe: 각 카테고리 정규화 가중치의 평균
    - 미인식 카테고리는 무시

    반환 예시:
        {"편의점": 0.875, "병원": 0.4375, ..., "공원": 1.094}
    """
    if not vibe_list:
        return {k: 1.0 for k in INFRA_KEYS}

    valid = [v for v in vibe_list if v in VIBE_RAW_SCORES]
    if not valid:
        return {k: 1.0 for k in INFRA_KEYS}

    normalized_list = [normalize_weights(VIBE_RAW_SCORES[v]) for v in valid]

    avg = {
        k: round(sum(d[k] for d in normalized_list) / len(normalized_list), 4)
        for k in INFRA_KEYS
    }
    return avg


def extract_vibe_from_text(text: str) -> Dict:
    """
    자연어 텍스트에서 vibe 카테고리 추출 (키워드 기반 폴백).

    LLM 연결 후에는 이 함수 대신 LLM 분류 결과를 사용.

    반환:
        {
            "matched": ["조용함", "자연친화"],   # 매칭된 카테고리
            "unrecognized": "역세권",            # 매칭 안 된 표현 (재질문용)
        }
    """
    matched = []
    for vibe, keywords in _VIBE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched.append(vibe)

    unrecognized = None
    for kw in _UNRECOGNIZED_KEYWORDS:
        if kw in text:
            unrecognized = kw
            break

    return {"matched": matched, "unrecognized": unrecognized}


def apply_vibe_to_infra_scores(
    raw_scores: Dict[str, float],
    vibe_weights: Dict[str, float],
) -> float:
    """
    인프라 7종 거리 점수 dict + vibe 가중치 dict → 가중 평균 점수 반환.

    raw_scores: {"편의점": 100, "병원": 30, ...}  (0/30/60/100 중 하나)
    vibe_weights: get_vibe_weights()의 반환값

    사용처: v5 인프라 점수 계산 시 vibe 가중치 적용
    """
    total_weight = sum(vibe_weights.get(k, 1.0) for k in raw_scores)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(
        raw_scores[k] * vibe_weights.get(k, 1.0) for k in raw_scores
    )
    return round(weighted_sum / total_weight, 2)


# ──────────────────────────────────────────────────────────
# 디버깅 / 출력 유틸
# ──────────────────────────────────────────────────────────

def print_vibe_weights(vibe_list: Optional[List[str]]) -> None:
    """선택된 vibe에 대한 가중치 표 출력 (디버깅 / Streamlit 디버그 패널용)."""
    weights = get_vibe_weights(vibe_list)
    label = " + ".join(vibe_list) if vibe_list else "균등(미선택)"
    print(f"\n[vibe 가중치] {label}")
    print(f"  {'인프라':<8} {'가중치':>6}")
    print(f"  {'─'*16}")
    for k in INFRA_KEYS:
        bar = "█" * int(weights[k] * 4)
        print(f"  {k:<8} {weights[k]:>6.3f}  {bar}")
    print(f"  {'─'*16}")
    print(f"  {'합계':<8} {sum(weights.values()):>6.3f}")


def get_vibe_display_name(vibe: str) -> str:
    """챗봇 선택지 표시용 설명 문구 반환."""
    _DISPLAY = {
        "조용함":    "① 조용함  — 공원·한적한 골목 선호",
        "번화함":    "② 번화함  — 카페·헬스장·편의점 밀집",
        "청년활기":  "③ 청년활기 — 카페·헬스장 중심, 트렌디",
        "가족친화":  "④ 가족친화 — 병원·약국·마트 중시",
        "자연친화":  "⑤ 자연친화 — 공원·녹지 최우선",
        "편의 우선": "⑥ 편의 우선 — 편의점·마트 가까운 곳",
        "운동·건강": "⑦ 운동·건강 — 헬스장·공원 동시 중시",
        "카페·문화": "⑧ 카페·문화 — 카페 많고 감성적인 동네",
    }
    return _DISPLAY.get(vibe, vibe)


def list_vibe_options() -> str:
    """챗봇용 vibe 선택지 문자열 반환."""
    lines = [get_vibe_display_name(v) for v in VIBE_CATEGORIES]
    lines.append("⑨ 분위기 상관없음 (균등 적용)")
    return "\n".join(lines)
