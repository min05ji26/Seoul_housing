"""
scripts/preprocess_sales_data.py
────────────────────────────────
expense_module 1단계 전처리 스크립트 (1회용).

입력:
  1) 서울시 상권분석서비스(추정매출-상권)_2024년.csv  (cp949, 87,179행 × 55컬럼)
  2) 서울시 상권분석서비스(영역-상권).shp + .dbf      (utf-8, 1,650 폴리곤, EPSG:5181)

처리:
  - 매출 CSV: 4분기(20244) + 4개 업종 필터 → 9개 컬럼 보존
  - 단가 컬럼 추가: avg_price = 당월_매출_금액 / 당월_매출_건수
    * 매출_건수 < 30 행은 NaN 처리 (소표본 outlier 제외)
  - 영역 shapefile → TRDAR_CD 별 자치구명 / 좌표(EPSG:5181 → 4326) 매핑
  - 매출 데이터에 자치구명 join

산출물:
  - data/sales_q4_processed.csv   (4분기 + 4개 업종, gu 컬럼 추가)
  - data/trading_area_to_gu.json  ({TRDAR_CD: {gu, name, lat, lon, category}})
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import shapefile  # pyshp
from pyproj import Transformer

# ─────────────────────────────────────────────────────────
# 경로 설정 (입력 파일 — 다운로드 폴더 직접 지정)
# ─────────────────────────────────────────────────────────
DOWNLOADS = Path(r"C:\Users\kj77k\Downloads")
SALES_CSV = DOWNLOADS / "예상생활비2" / "서울시 상권분석서비스(추정매출-상권)_2024년" / "서울시 상권분석서비스(추정매출-상권)_2024년.csv"
SHP_PATH  = DOWNLOADS / "서울시 상권분석서비스(영역-상권)" / "서울시 상권분석서비스(영역-상권).shp"

# 출력 (프로젝트 루트 기준)
ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "data"
OUT_CSV  = OUT_DIR / "sales_q4_processed.csv"
OUT_JSON = OUT_DIR / "trading_area_to_gu.json"

# 필터 기준
TARGET_QUARTER = 20244
TARGET_INDUSTRY_CODES = {
    "CS100001": "한식음식점",
    "CS100010": "커피-음료",
    "CS300001": "슈퍼마켓",
    "CS300002": "편의점",
}
MIN_TRANSACTION_COUNT = 30  # 단가 계산 시 최소 매출 건수


# ─────────────────────────────────────────────────────────
# 1. 매출 CSV 전처리
# ─────────────────────────────────────────────────────────
def load_sales_q4() -> pd.DataFrame:
    """4분기 + 4개 업종 + 9개 컬럼만 추출. 단가(avg_price) 컬럼 추가."""
    keep_cols = [
        "기준_년분기_코드",
        "상권_구분_코드", "상권_구분_코드_명",
        "상권_코드", "상권_코드_명",
        "서비스_업종_코드", "서비스_업종_코드_명",
        "당월_매출_금액", "당월_매출_건수",
    ]

    print(f"[1/4] 매출 CSV 로드: {SALES_CSV.name}")
    df = pd.read_csv(SALES_CSV, encoding="cp949", usecols=keep_cols)
    print(f"      전체 {len(df):,}행 → ", end="")

    # 4분기 + 4개 업종 필터
    df = df[df["기준_년분기_코드"] == TARGET_QUARTER].copy()
    df = df[df["서비스_업종_코드"].isin(TARGET_INDUSTRY_CODES.keys())].copy()
    print(f"4분기+4업종 {len(df):,}행")

    # 단가 컬럼 (매출_건수 < 30 → NaN)
    cnt = df["당월_매출_건수"].astype(float)
    amt = df["당월_매출_금액"].astype(float)
    invalid = (cnt < MIN_TRANSACTION_COUNT) | (cnt == 0)
    df["avg_price"] = (amt / cnt).where(~invalid, other=pd.NA)
    n_nan = int(invalid.sum())
    print(f"      단가 NaN 처리(매출건수<{MIN_TRANSACTION_COUNT}): {n_nan}건")

    # 상권_코드는 string으로 통일 (shapefile과 join 용)
    df["상권_코드"] = df["상권_코드"].astype(str)
    return df


# ─────────────────────────────────────────────────────────
# 2. 영역 shapefile → 상권 메타 dict
# ─────────────────────────────────────────────────────────
def load_trading_area_map() -> dict:
    """TRDAR_CD → {gu, name, lat, lon, category} dict 생성.

    shapefile 좌표는 EPSG:5181 (Korea Central Belt) → EPSG:4326 (WGS84) 변환.
    XCNTS_VALU/YDNTS_VALU는 단위가 미터이므로 항상 정수형으로 들어와도 OK.
    """
    print(f"[2/4] Shapefile 로드: {SHP_PATH.name}")
    sf = shapefile.Reader(str(SHP_PATH), encoding="utf-8")
    fields = [f[0] for f in sf.fields[1:]]
    idx = {name: fields.index(name) for name in [
        "TRDAR_CD", "TRDAR_CD_N", "TRDAR_SE_1",
        "XCNTS_VALU", "YDNTS_VALU", "SIGNGU_CD_",
    ]}

    transformer = Transformer.from_crs("EPSG:5181", "EPSG:4326", always_xy=True)

    result = {}
    for rec in sf.records():
        x = float(rec[idx["XCNTS_VALU"]])
        y = float(rec[idx["YDNTS_VALU"]])
        lon, lat = transformer.transform(x, y)
        cd = str(rec[idx["TRDAR_CD"]])
        result[cd] = {
            "gu":       rec[idx["SIGNGU_CD_"]],
            "name":     rec[idx["TRDAR_CD_N"]],
            "lat":      round(lat, 6),
            "lon":      round(lon, 6),
            "category": rec[idx["TRDAR_SE_1"]],   # 골목상권/발달상권/전통시장/관광특구
        }
    sf.close()
    print(f"      상권 {len(result):,}개 (25개 구)")
    return result


# ─────────────────────────────────────────────────────────
# 3. 매출 + 자치구명 join
# ─────────────────────────────────────────────────────────
def attach_gu(df: pd.DataFrame, area_map: dict) -> pd.DataFrame:
    df["gu"]  = df["상권_코드"].map(lambda c: area_map.get(c, {}).get("gu"))
    df["lat"] = df["상권_코드"].map(lambda c: area_map.get(c, {}).get("lat"))
    df["lon"] = df["상권_코드"].map(lambda c: area_map.get(c, {}).get("lon"))

    n_unmatched = int(df["gu"].isna().sum())
    print(f"[3/4] 자치구 매핑: {len(df) - n_unmatched:,}/{len(df):,} (누락 {n_unmatched})")
    if n_unmatched:
        miss = df[df["gu"].isna()]["상권_코드"].unique()[:10]
        print(f"      누락 상권 샘플: {list(miss)}")
    return df


# ─────────────────────────────────────────────────────────
# 4. 저장
# ─────────────────────────────────────────────────────────
def save_outputs(df: pd.DataFrame, area_map: dict) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"[4/4] 저장: {OUT_CSV.relative_to(ROOT)} ({len(df):,}행)")

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(area_map, f, ensure_ascii=False, indent=2)
    print(f"      저장: {OUT_JSON.relative_to(ROOT)} ({len(area_map):,}개)")


# ─────────────────────────────────────────────────────────
# 미리보기 출력 (사용자 검증용)
# ─────────────────────────────────────────────────────────
def show_preview(df: pd.DataFrame, area_map: dict) -> None:
    print()
    print("=" * 78)
    print("미리보기 1: 4개 업종 × 25개 구 평균단가 매트릭스 (단위: 원)")
    print("=" * 78)
    pivot = (df.dropna(subset=["avg_price", "gu"])
               .groupby(["gu", "서비스_업종_코드_명"])["avg_price"]
               .mean()
               .unstack())
    # 4개 업종 순서 고정
    industry_order = ["한식음식점", "커피-음료", "슈퍼마켓", "편의점"]
    pivot = pivot[[c for c in industry_order if c in pivot.columns]]
    # 천 단위 콤마 + 정수
    pivot_fmt = pivot.map(lambda v: f"{int(round(v)):,}" if pd.notna(v) else "—")
    print(pivot_fmt.to_string())

    print()
    print("=" * 78)
    print("미리보기 2: trading_area_to_gu.json 샘플 (앞 5개)")
    print("=" * 78)
    sample = dict(list(area_map.items())[:5])
    print(json.dumps(sample, ensure_ascii=False, indent=2))


# ─────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────
def main() -> None:
    sales = load_sales_q4()
    area_map = load_trading_area_map()
    sales = attach_gu(sales, area_map)
    save_outputs(sales, area_map)
    show_preview(sales, area_map)


if __name__ == "__main__":
    main()
