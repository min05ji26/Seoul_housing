"""
feedback_module.py
──────────────────
만족도 피드백 수집 → CSV 누적 저장 모듈
V5 (housing_recommendation_v5.py) 결과 출력 후 호출

기능:
  - 추천 결과에 대한 사용자 만족도 수집 (만족/보통/불만족)
  - 개별 매물별 관심 여부 수집 (y/n)
  - CSV에 누적 저장 (다음 실행 시 기존 데이터에 추가)
  - 저장된 피드백 통계 요약 출력
  - 향후 학습 기반 가중치 보정에 활용할 수 있는 구조

CSV 컬럼:
  timestamp, session_id, rank, address, gu, dong,
  commute_time_min, conv_deposit_manwon, area_m2,
  housing_type, final_score, commute_score, housing_score,
  infra_score, policy_score,
  user_satisfaction, user_interest,
  weight_commute, weight_housing, weight_infra,
  transport_mode, budget_manwon, allowed_commute_min
"""

import os
import datetime
import uuid

import pandas as pd
from typing import Optional


# ──────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────
FEEDBACK_CSV_DIR = r"C:\Users\kj77k\Downloads\서울살이_프로젝트\api코드결과"
FEEDBACK_CSV_NAME = "recommendation_feedback.csv"

FEEDBACK_COLUMNS = [
    "timestamp", "session_id", "rank", "address", "gu", "dong",
    "commute_time_min", "conv_deposit_manwon", "area_m2",
    "housing_type", "final_score", "commute_score", "housing_score",
    "infra_score", "policy_score",
    "user_satisfaction", "user_interest",
    "weight_commute", "weight_housing", "weight_infra",
    "transport_mode", "budget_manwon", "allowed_commute_min",
]


# ──────────────────────────────────────────────────────────
# CSV 파일 관리
# ──────────────────────────────────────────────────────────
def _get_feedback_path() -> str:
    return os.path.join(FEEDBACK_CSV_DIR, FEEDBACK_CSV_NAME)


def _load_existing_feedback() -> pd.DataFrame:
    """기존 피드백 CSV 로드 (없으면 빈 DataFrame 반환)"""
    path = _get_feedback_path()
    if os.path.exists(path):
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except Exception:
            return pd.DataFrame(columns=FEEDBACK_COLUMNS)
    return pd.DataFrame(columns=FEEDBACK_COLUMNS)


def _save_feedback(df: pd.DataFrame) -> str:
    """피드백 DataFrame을 CSV에 저장"""
    path = _get_feedback_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path
    except PermissionError:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        alt = path.replace(".csv", f"_{ts}.csv")
        df.to_csv(alt, index=False, encoding="utf-8-sig")
        return alt


# ──────────────────────────────────────────────────────────
# 피드백 수집
# ──────────────────────────────────────────────────────────
def collect_feedback(final_df: pd.DataFrame,
                      weight_commute: float,
                      weight_housing: float,
                      weight_infra: float = 0.0,
                      transport_mode: str = "",
                      budget_manwon: Optional[float] = None,
                      allowed_commute_min: int = 90) -> Optional[str]:
    """
    추천 결과에 대한 사용자 만족도 피드백 수집.

    Parameters
    ----------
    final_df          : 최종 추천 결과 DataFrame
    weight_commute    : 통근 가중치
    weight_housing    : 주거비 가중치
    weight_infra      : 인프라 가중치
    transport_mode    : 이동수단
    budget_manwon     : 예산 (환산보증금)
    allowed_commute_min: 허용 통근시간

    Returns
    -------
    str : 저장된 CSV 파일 경로 (None이면 피드백 건너뜀)
    """
    print("\n" + "=" * 60)
    print("  추천 결과 만족도 피드백")
    print("=" * 60)

    skip = input("\n  피드백을 남기시겠습니까? (y=예 / n=건너뜀): ").strip().lower()
    if skip != "y":
        print("  → 피드백 건너뜀")
        return None

    # 전체 만족도
    print("\n  전체 추천 결과에 대한 만족도:")
    print("    1=만족  2=보통  3=불만족")
    while True:
        sat_input = input("  선택: ").strip()
        if sat_input in ("1", "2", "3"):
            break
        print("  ※ 1, 2, 3 중 하나를 선택해 주세요.")

    satisfaction_map = {"1": "만족", "2": "보통", "3": "불만족"}
    overall_satisfaction = satisfaction_map[sat_input]

    # 세션 ID 생성
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    timestamp  = datetime.datetime.now().isoformat()

    # 개별 매물 관심 여부
    print(f"\n  개별 매물에 대한 관심 여부 (y=관심 / n=관심없음 / Enter=건너뜀):")
    rows = []

    for i, row in final_df.iterrows():
        addr = (row.get("display_address") or row.get("matched_address")
                or row.get("candidate_address", ""))
        score = row.get("final_score", "")

        interest_input = input(f"    [{i+1}] {addr[:40]}... (점수:{score:.0f}) → ").strip().lower()
        interest = ""
        if interest_input == "y":
            interest = "관심"
        elif interest_input == "n":
            interest = "비관심"
        # 빈칸이면 미응답

        fb_row = {
            "timestamp":            timestamp,
            "session_id":           session_id,
            "rank":                 i + 1,
            "address":              addr,
            "gu":                   row.get("시군구_2", ""),
            "dong":                 row.get("읍면동", "") or row.get("dong", ""),
            "commute_time_min":     row.get("commute_time_min"),
            "conv_deposit_manwon":  row.get("conv_deposit_manwon"),
            "area_m2":              row.get("area_m2"),
            "housing_type":         row.get("housing_type", ""),
            "final_score":          row.get("final_score"),
            "commute_score":        row.get("commute_score"),
            "housing_score":        row.get("housing_score"),
            "infra_score":          row.get("infra_score"),
            "policy_score":         row.get("policy_score"),
            "user_satisfaction":    overall_satisfaction,
            "user_interest":        interest,
            "weight_commute":       weight_commute,
            "weight_housing":       weight_housing,
            "weight_infra":         weight_infra,
            "transport_mode":       transport_mode,
            "budget_manwon":        budget_manwon,
            "allowed_commute_min":  allowed_commute_min,
        }
        rows.append(fb_row)

    if not rows:
        print("  → 피드백 데이터 없음")
        return None

    # 기존 데이터에 추가
    existing = _load_existing_feedback()
    new_df   = pd.DataFrame(rows)
    combined = pd.concat([existing, new_df], ignore_index=True)

    saved_path = _save_feedback(combined)
    print(f"\n  ✅ 피드백 저장 완료: {saved_path}")
    print(f"     누적 피드백: {len(combined)}건 (이번 세션: {len(rows)}건)")

    return saved_path


# ──────────────────────────────────────────────────────────
# 피드백 통계 요약
# ──────────────────────────────────────────────────────────
def print_feedback_summary() -> None:
    """
    저장된 피드백 CSV 통계 요약 출력.
    (향후 학습 기반 가중치 보정 단계로 연결할 수 있는 기초 통계)
    """
    df = _load_existing_feedback()
    if df.empty:
        print("  [피드백 통계] 저장된 피드백이 없습니다.")
        return

    total = len(df)
    sessions = df["session_id"].nunique()

    print(f"\n  [피드백 통계]")
    print(f"    · 총 피드백 건수: {total}건 ({sessions}세션)")

    # 만족도 분포
    if "user_satisfaction" in df.columns:
        sat_counts = df["user_satisfaction"].value_counts()
        print(f"    · 만족도 분포:")
        for sat, cnt in sat_counts.items():
            pct = cnt / total * 100
            print(f"        {sat}: {cnt}건 ({pct:.0f}%)")

    # 관심 매물 비율
    interest_df = df[df["user_interest"] != ""]
    if not interest_df.empty:
        interested = (interest_df["user_interest"] == "관심").sum()
        not_interested = (interest_df["user_interest"] == "비관심").sum()
        print(f"    · 관심 매물: {interested}건 / 비관심: {not_interested}건")

    # 관심 매물의 평균 점수 vs 비관심 매물
    for label in ["관심", "비관심"]:
        subset = df[df["user_interest"] == label]
        if len(subset) >= 2:
            avg_score = subset["final_score"].mean()
            avg_commute = subset["commute_time_min"].mean()
            avg_price = subset["conv_deposit_manwon"].mean()
            print(f"    · [{label}] 평균 점수: {avg_score:.1f} / "
                  f"통근: {avg_commute:.0f}분 / 환산보증금: {avg_price:.0f}만원")

    # 단계별 분석 가이드
    if total >= 30:
        print(f"    📊 30건 이상 → 기초 통계 분석 가능")
    if total >= 50:
        print(f"    📊 50건 이상 → 상관관계 분석 가능 (핵심 변수 파악)")
    if total >= 200:
        print(f"    📊 200건 이상 → 머신러닝 기반 가중치 자동 보정 가능")

    print(f"    현재 누적: {total}건")


def get_feedback_count() -> int:
    """현재 저장된 피드백 건수 반환"""
    df = _load_existing_feedback()
    return len(df)
