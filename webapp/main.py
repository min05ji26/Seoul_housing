"""
webapp/main.py
──────────────
FastAPI 백엔드

엔드포인트:
  GET  /              → index.html
  GET  /static/*      → CSS / JS
  GET  /api/health    → 서버 상태
  POST /api/chat      → 챗봇 1턴
  POST /api/recommend → v5 추천 실행
"""

import os
import sys
import io
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# 프로젝트 루트를 sys.path에 추가 (상위 폴더의 모듈 import)
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from nlp_input_module import ChatBot

# ──────────────────────────────────────────────────────────
app = FastAPI(title="서울살이 챗봇 API")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ──────────────────────────────────────────────────────────
# 세션 저장소 (프로세스 내 메모리)
# ──────────────────────────────────────────────────────────
_sessions: Dict[str, ChatBot] = {}


def _get_bot(session_id: str) -> ChatBot:
    if session_id not in _sessions:
        _sessions[session_id] = ChatBot()
    return _sessions[session_id]


# ──────────────────────────────────────────────────────────
# Pydantic 모델
# ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_message: str
    session_id: Optional[str] = None


class RecommendRequest(BaseModel):
    session_id: str


# ──────────────────────────────────────────────────────────
# 라우트
# ──────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    bot = _get_bot(session_id)

    reply, is_done, v5_params = bot.process(req.user_message)

    # 슬롯 현황
    slot_status = bot.slot_status()

    # 빠른 옵션 버튼 결정
    missing = bot._missing_required()
    quick_options = _quick_options_for(missing[0] if missing else None, bot)

    return {
        "session_id":   session_id,
        "bot_message":  reply,
        "slot_status":  slot_status,
        "quick_options": quick_options,
        "is_complete":  is_done,
        "v5_params":    v5_params if is_done else None,
    }


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    bot = _get_bot(req.session_id)
    if not bot._done:
        return JSONResponse(status_code=400, content={"error": "슬롯 미완성"})

    v5_params = bot.get_v5_params()

    import glob as glob_mod
    csv_files = sorted(glob_mod.glob(str(ROOT / "사용_csv_모음" / "*.csv")))
    if not csv_files:
        return JSONResponse(status_code=500, content={"error": "주거지 CSV 없음"})

    csv_path = csv_files[0]

    # stdout 캡처
    log_buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = log_buf

    try:
        import youth_policy_module
        youth_policy_module._TEST_MODE = True

        from housing_recommendation_v5 import run_recommendation
        final_df, seoul_avg = run_recommendation(
            housing_csv_path=csv_path,
            **v5_params,
        )

        results = _df_to_list(final_df)
        return {
            "results":    results,
            "seoul_avg":  seoul_avg,
            "log":        log_buf.getvalue()[-2000:],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        sys.stdout = old_stdout
        import youth_policy_module
        youth_policy_module._TEST_MODE = False


# ──────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────

def _df_to_list(df) -> list:
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "gu":          str(row.get("시군구_2", "")),
            "dong":        str(row.get("읍면동", "")),
            "house_type":  str(row.get("주택유형", "")),
            "score":       round(float(row.get("topsis_score", 0)), 4),
            "price_manwon": int(row.get("환산보증금(만원)", 0)),
            "commute_min": int(row.get("예상_통근시간(분)", 0)),
            "infra_score": row.get("infra_score"),
            "policy_score": row.get("policy_score"),
        })
    return rows


def _quick_options_for(slot: Optional[str], bot: ChatBot) -> list:
    if slot == "transport_mode":
        return [{"label": "자가용", "value": "자가용"}, {"label": "대중교통", "value": "대중교통"}]
    if slot == "rent_type":
        return [{"label": "전세", "value": "전세"}, {"label": "월세", "value": "월세"}]
    if slot == "house_type":
        return [
            {"label": "오피스텔", "value": "① 오피스텔"},
            {"label": "연립·다세대", "value": "② 연립다세대"},
            {"label": "상관없음", "value": "③"},
        ]
    if slot == "weight_preference":
        return [
            {"label": "통근 우선", "value": "① 통근 우선"},
            {"label": "주거비 우선", "value": "② 주거비 우선"},
            {"label": "균형", "value": "③ 균형"},
            {"label": "알아서 해줘", "value": "④ 알아서 해줘"},
        ]
    # vibe 질문 중
    if bot._asked_vibe and bot.slots.get("vibe") is None:
        return [
            {"label": "조용함", "value": "① 조용함"},
            {"label": "번화함", "value": "② 번화함"},
            {"label": "청년활기", "value": "③ 청년활기"},
            {"label": "카페·문화", "value": "⑧ 카페·문화"},
            {"label": "상관없음", "value": "⑨ 상관없음"},
        ]
    # 청년정책 질문 중
    if bot._asked_policy and bot.slots.get("use_youth_policy") is None:
        return [{"label": "예", "value": "예"}, {"label": "아니요", "value": "아니요"}]
    return []
