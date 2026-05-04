"""
job_search_module.py
────────────────────
서울시 채용정보 API → work_address 변환 모듈
V5 (housing_recommendation_v5.py) main() 함수에 연결

사용 API:
  GetJobInfo : 민간 채용정보 (서울시 일자리포털)
               기업주소(BASS_ADRES_CN) → work_address로 연결
"""

import os
import re
import time
import requests
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# ──────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────
SEOUL_JOB_API_KEY = os.getenv("SEOUL_JOB_API_KEY", "")
SEOUL_API_BASE    = "http://openapi.seoul.go.kr:8088"
REQUEST_TIMEOUT   = 20
SLEEP_BETWEEN     = 0.3
MAX_JOB_RESULTS   = 100   # 1회 조회 최대 건수


# ──────────────────────────────────────────────────────────
# 공통 호출
# ──────────────────────────────────────────────────────────
def _call_seoul_api(service: str, start: int, end: int,
                    extra_params: str = "") -> dict:
    url = f"{SEOUL_API_BASE}/{SEOUL_JOB_API_KEY}/json/{service}/{start}/{end}/{extra_params}"
    resp = requests.get(url.rstrip("/"), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    svc  = data.get(service, {})
    code = svc.get("RESULT", {}).get("CODE", "")
    if code and code not in ("INFO-000", "INFO-200"):
        msg = svc.get("RESULT", {}).get("MESSAGE", "")
        raise ValueError(f"[서울시 API 오류] {code}: {msg}")
    return svc


# ──────────────────────────────────────────────────────────
# ① GetJobInfo 검색 (민간 채용정보)
# ──────────────────────────────────────────────────────────
def search_jobs_getjobinfo(work_region: str = "",
                            career_code: str = "",
                            employ_code: str = "",
                            reg_date:    str = "") -> list[dict]:
    """
    GetJobInfo API 호출 → 구인공고 목록 반환

    Parameters
    ----------
    work_region  : 근무예정지 주소 키워드 (예: "강남구", "서울")
    career_code  : 경력코드 (J01301=신입, J01302=경력, J01300=무관, ""=전체)
    employ_code  : 고용형태코드 (J01101=상용직, J01102=계약직, ""=전체)
    reg_date     : 등록일 필터 (예: "2026-04-01", ""=전체)

    Returns
    -------
    list[dict] : row 데이터 리스트
    """
    # URL 파라미터 순서: ACDMCR / EMPLYM_STLE / WORK_PARAR / CAREER / JO_REG_DT
    # 선택항목은 빈칸으로 스킵 가능
    params = "/".join([
        "",           # 학력코드 (전체)
        employ_code,  # 고용형태코드
        work_region,  # 근무예정지
        career_code,  # 경력조건
        reg_date,     # 등록일
    ]).rstrip("/")

    # 전체 건수 먼저 파악
    try:
        svc = _call_seoul_api("GetJobInfo", 1, 1, params)
    except Exception as e:
        print(f"  [GetJobInfo 오류] {e}")
        return []

    total = int(svc.get("list_total_count", 0))
    if total == 0:
        return []

    # 최대 MAX_JOB_RESULTS 건 조회
    end   = min(total, MAX_JOB_RESULTS)
    try:
        svc   = _call_seoul_api("GetJobInfo", 1, end, params)
        return svc.get("row", [])
    except Exception as e:
        print(f"  [GetJobInfo 조회 오류] {e}")
        return []


# ──────────────────────────────────────────────────────────
# 주소 정제 함수
# ──────────────────────────────────────────────────────────
def clean_address(addr: str) -> str:
    """
    GetJobInfo BASS_ADRES_CN 주소 정제
    예) "서울특별시 동대문구 왕산로 191 -1 (청량리동) 402호 청량리동 동원빌딩"
     → "서울특별시 동대문구 왕산로 191-1"  (괄호·중복 제거)
    """
    if not addr:
        return ""
    # 괄호 내용 제거 (예: (주엽동))
    s = re.sub(r"\([^)]*\)", "", addr)
    # 중복 공백 정리
    s = re.sub(r"\s+", " ", s).strip()
    # 건물명/호수 뒤 잡음 제거 (숫자 이후 한글만 있는 토큰)
    # 예: "191 -1 402호 청량리동 동원빌딩" → "191-1 402호" 수준까지만
    s = re.sub(r"\s+-\s+", "-", s)   # "191 -1" → "191-1"
    return s


def is_seoul_address(addr: str) -> bool:
    return "서울" in addr


# ──────────────────────────────────────────────────────────
# 직종 키워드 → GetJobInfo 결과 필터링
# ──────────────────────────────────────────────────────────
def filter_by_keyword(rows: list[dict], keyword: str) -> list[dict]:
    """
    구인제목(JO_SJ), 직종명(JOBCODE_NM), 업무내용(DTY_CN)에서
    키워드 포함 공고만 추출
    """
    if not keyword:
        return rows
    kw = keyword.strip().lower()
    result = []
    for r in rows:
        targets = " ".join([
            str(r.get("JO_SJ", "")),
            str(r.get("JOBCODE_NM", "")),
            str(r.get("DTY_CN", "")),
            str(r.get("BSNS_SUMRY_CN", "")),
        ]).lower()
        if kw in targets:
            result.append(r)
    return result


# ──────────────────────────────────────────────────────────
# 공고 목록 출력
# ──────────────────────────────────────────────────────────
def print_job_list(rows: list[dict]) -> None:
    if not rows:
        print("  ※ 조건에 맞는 채용공고가 없습니다.")
        return

    print(f"\n  총 {len(rows)}건의 채용공고\n")
    for i, r in enumerate(rows, 1):
        addr      = clean_address(r.get("BASS_ADRES_CN", ""))
        work_area = r.get("WORK_PARAR_BASS_ADRES_CN", "")
        seoul_ok  = "✅" if is_seoul_address(addr) else "⚠️ 서울 외"
        print(f"  [{i:>2}] {r.get('CMPNY_NM','')}")
        print(f"        직무: {r.get('JO_SJ','')[:50]}")
        print(f"        고용: {r.get('EMPLYM_STLE_CMMN_MM','')} / "
              f"급여: {r.get('HOPE_WAGE','').strip()} / "
              f"경력: {r.get('CAREER_CND_NM','')}")
        print(f"        근무지역: {work_area}")
        print(f"        기업주소: {addr}  {seoul_ok}")
        print(f"        마감: {r.get('RCEPT_CLOS_NM','')}")
        print()


# ──────────────────────────────────────────────────────────
# 메인 진입점: 직장 없음 선택 시 호출되는 함수
# ──────────────────────────────────────────────────────────
def job_search_flow() -> Optional[str]:
    """
    직장을 찾는 사용자 대화 흐름
    채용공고 목록 표시 → 사용자가 번호 선택 → work_address 반환

    Returns
    -------
    str  : 선택한 공고의 기업주소 (work_address로 사용)
    None : 사용자가 취소하거나 주소를 얻지 못한 경우
    """
    while True:  # 재귀 대신 반복문
        print("\n" + "="*60)
        print("  채용정보 검색 (직장을 찾고 있는 경우)")
        print("="*60)

        # ── 직종 키워드 입력 ──────────────────────────────────
        keyword = input("\n  희망 직종 키워드 (예: 개발자, 간호사, 사무, 비우면 전체): ").strip()

        # ── 근무 희망 지역 ────────────────────────────────────
        region = input("  희망 근무지역 (예: 강남구, 종로구, 비우면 서울 전체): ").strip()

        # ── 경력 조건 ─────────────────────────────────────────
        print("  경력 조건: 1=신입  2=경력  3=무관")
        career_input = input("  선택 (비우면 전체): ").strip()
        career_map   = {"1": "J01301", "2": "J01302", "3": "J01300"}
        career_code  = career_map.get(career_input, "")  # 비우면 전체 조회

        # ── 고용 형태 ─────────────────────────────────────────
        print("  고용 형태: 1=정규직  2=계약직  3=파트타임 정규직  4=아르바이트")
        employ_input = input("  선택 (비우면 전체): ").strip()
        employ_map   = {"1": "J01101", "2": "J01102", "3": "J01105", "4": "J01103"}
        employ_code  = employ_map.get(employ_input, "")

        print(f"\n  [채용정보] 검색 중... (키워드: '{keyword or '전체'}', 지역: '{region or '서울 전체'}')")

        rows = search_jobs_getjobinfo(
            work_region = region,
            career_code = career_code,
            employ_code = employ_code,
        )

        # 키워드 필터 (클라이언트 측)
        if keyword:
            rows = filter_by_keyword(rows, keyword)

        # 서울 주소 공고만 사용 (서울 외 제거)
        rows_seoul = [r for r in rows if is_seoul_address(
                      clean_address(r.get("BASS_ADRES_CN","")))]
        removed = len(rows) - len(rows_seoul)
        if removed > 0:
            print(f"  [필터] 서울 외 기업주소 {removed}건 제외")

        if not rows_seoul:
            print("\n  ※ 서울 소재 기업 공고가 없습니다. 키워드나 지역 조건을 완화해 보세요.")
            retry = input("\n  다시 검색하시겠습니까? (y / n): ").strip().lower()
            if retry != "y":
                return None
            continue

        # 상위 20건만 표시
        display_rows = rows_seoul[:20]
        print_job_list(display_rows)

        # ── 번호 선택 ─────────────────────────────────────────
        while True:
            sel = input(f"\n  공고 번호를 선택하세요 (1~{len(display_rows)}, 0=다시검색): ").strip()
            if sel == "0":
                break  # 내부 while 탈출 → 외부 while로 다시 검색
            if sel.isdigit() and 1 <= int(sel) <= len(display_rows):
                chosen   = display_rows[int(sel) - 1]
                raw_addr = chosen.get("BASS_ADRES_CN", "").strip()
                addr     = clean_address(raw_addr)

                print(f"\n  선택한 공고: {chosen.get('JO_SJ','')}")
                print(f"  기업명    : {chosen.get('CMPNY_NM','')}")
                print(f"  기업주소  : {addr}")

                if not addr:
                    print("  ⚠️  기업주소를 가져올 수 없습니다. 직접 입력해 주세요.")
                    addr = input("  직접 입력 (취소하려면 비우고 Enter): ").strip()
                    if not addr:
                        continue

                print(f"\n  ✅ 직장 주소 설정: {addr}")
                return addr
            print(f"  ※ 1~{len(display_rows)} 사이의 번호 또는 0을 입력해 주세요.")
