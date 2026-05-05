"""
webapp/user.py
──────────────
사용자 정보, 검색조건, 추천이력 라우터

엔드포인트:
  GET    /user/{user_id}                  - 내 정보
  PATCH  /user/{user_id}/nickname         - 닉네임 변경
  POST   /user/{user_id}/conditions       - 검색조건 저장
  GET    /user/{user_id}/conditions       - 저장된 검색조건 목록
  POST   /user/{user_id}/recommendations  - 추천 이력 저장
  GET    /user/{user_id}/recommendations  - 추천 이력 조회
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from webapp.database import get_conn

router = APIRouter()


# ── 내 정보 조회 ─────────────────────────────────────────
@router.get("/{user_id}")
def get_user(user_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, nickname, email, created_at FROM users WHERE id=?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return dict(row)


# ── 닉네임 수정 ──────────────────────────────────────────
class UpdateNicknameRequest(BaseModel):
    nickname: str


@router.patch("/{user_id}/nickname")
def update_nickname(user_id: int, req: UpdateNicknameRequest):
    conn = get_conn()
    try:
        cur = conn.execute("UPDATE users SET nickname=? WHERE id=?", (req.nickname, user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        conn.commit()
    finally:
        conn.close()
    return {"message": "닉네임 변경 완료", "nickname": req.nickname}


# ── 검색조건 저장 ────────────────────────────────────────
class SearchConditionRequest(BaseModel):
    workplace:      Optional[str] = None
    transport:      Optional[str] = None
    contract_type:  Optional[str] = None
    deposit:        Optional[int] = None
    monthly_rent:   Optional[int] = None
    commute_time:   Optional[int] = None
    preferred_area: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time:   Optional[str] = None
    house_type:     Optional[str] = None
    priority:       Optional[str] = None
    amenities:      Optional[str] = None
    youth_policy:   Optional[int] = None
    age:            Optional[int] = None


_COND_COLS = [
    "workplace", "transport", "contract_type", "deposit", "monthly_rent",
    "commute_time", "preferred_area", "departure_time", "arrival_time",
    "house_type", "priority", "amenities", "youth_policy", "age",
]


@router.post("/{user_id}/conditions")
def save_condition(user_id: int, req: SearchConditionRequest):
    data = req.dict()
    cols = ["user_id"] + _COND_COLS
    vals = [user_id] + [data[c] for c in _COND_COLS]
    placeholders = ",".join("?" * len(cols))

    conn = get_conn()
    try:
        cur = conn.execute(
            f"INSERT INTO search_conditions ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        conn.commit()
        cid = cur.lastrowid
    finally:
        conn.close()
    return {"message": "검색 조건 저장 완료", "condition_id": cid}


@router.get("/{user_id}/conditions")
def get_conditions(user_id: int):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM search_conditions WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ── 추천 이력 ────────────────────────────────────────────
class RecommendationRequest(BaseModel):
    workplace:     Optional[str] = None
    contract_type: Optional[str] = None
    budget:        Optional[str] = None
    commute_time:  Optional[int] = None
    result_count:  Optional[int] = None
    top_result:    Optional[str] = None


_REC_COLS = ["workplace", "contract_type", "budget", "commute_time", "result_count", "top_result"]


@router.post("/{user_id}/recommendations")
def save_recommendation(user_id: int, req: RecommendationRequest):
    data = req.dict()
    cols = ["user_id"] + _REC_COLS
    vals = [user_id] + [data[c] for c in _REC_COLS]
    placeholders = ",".join("?" * len(cols))

    conn = get_conn()
    try:
        cur = conn.execute(
            f"INSERT INTO recommendation_history ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        conn.commit()
        rid = cur.lastrowid
    finally:
        conn.close()
    return {"message": "추천 이력 저장 완료", "id": rid}


@router.get("/{user_id}/recommendations")
def get_recommendations(user_id: int):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM recommendation_history WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
