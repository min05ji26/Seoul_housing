"""
webapp/checklist.py
───────────────────
이사 체크리스트 라우터 (사용자별)
첫 호출 시 13개 기본 항목 자동 시드.

엔드포인트:
  GET    /checklist?user_id=1            - 목록 조회 (없으면 자동 시드)
  POST   /checklist?user_id=1            - 사용자 항목 추가
  PATCH  /checklist/{item_id}?user_id=1  - 체크 토글
  DELETE /checklist/{item_id}?user_id=1  - 항목 삭제
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from webapp.database import get_conn

router = APIRouter()


DEFAULT_CHECKLIST = [
    {"content": "이삿짐센터 예약하기",         "category": "이사전"},
    {"content": "박스/테이프/에어캡 구매하기", "category": "이사전"},
    {"content": "계절 지난 옷 먼저 박스에 넣기", "category": "이사전"},
    {"content": "안 쓰는 물건 정리하기",       "category": "이사전"},
    {"content": "전입신고 날짜 확인하기",      "category": "이사전"},
    {"content": "냉장고 음식 미리 비우기",     "category": "이사당일"},
    {"content": "귀중품은 직접 챙기기",        "category": "이사당일"},
    {"content": "가스/전기/수도 마지막 확인",  "category": "이사당일"},
    {"content": "전 집 열쇠 반납하기",         "category": "이사당일"},
    {"content": "주소 변경 (은행, 카드사, 택배)", "category": "이사후"},
    {"content": "전입신고하기 (14일 이내)",    "category": "이사후"},
    {"content": "확정일자 받기",               "category": "이사후"},
    {"content": "인터넷/TV 설치 신청",         "category": "이사후"},
]


def _seed_default(conn, user_id: int):
    cur = conn.cursor()
    for item in DEFAULT_CHECKLIST:
        cur.execute(
            "INSERT INTO checklist_items (user_id, content, category, is_default) VALUES (?,?,?,1)",
            (user_id, item["content"], item["category"]),
        )
    conn.commit()


@router.get("")
def get_checklist(user_id: int):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM checklist_items WHERE user_id=?", (user_id,)
        ).fetchall()
        if not rows:
            _seed_default(conn, user_id)
            rows = conn.execute(
                "SELECT * FROM checklist_items WHERE user_id=?", (user_id,)
            ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


class AddChecklistRequest(BaseModel):
    content:  str
    category: str


@router.post("")
def add_checklist(user_id: int, req: AddChecklistRequest):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO checklist_items (user_id, content, category, is_default) VALUES (?,?,?,0)",
            (user_id, req.content, req.category),
        )
        conn.commit()
        item_id = cur.lastrowid
        row = conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone()
    finally:
        conn.close()
    return dict(row)


@router.patch("/{item_id}")
def toggle_checklist(item_id: int, user_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM checklist_items WHERE id=? AND user_id=?", (item_id, user_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다")
        new_val = 0 if row["is_checked"] == 1 else 1
        conn.execute("UPDATE checklist_items SET is_checked=? WHERE id=?", (new_val, item_id))
        conn.commit()
        row = conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone()
    finally:
        conn.close()
    return dict(row)


@router.delete("/{item_id}")
def delete_checklist(item_id: int, user_id: int):
    conn = get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM checklist_items WHERE id=? AND user_id=?", (item_id, user_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다")
        conn.commit()
    finally:
        conn.close()
    return {"message": "삭제 완료"}
