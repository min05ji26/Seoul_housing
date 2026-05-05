"""
webapp/database.py
──────────────────
SQLite (Python 내장) 기반 DB 초기화 + CRUD 헬퍼
SQLAlchemy 미사용 (greenlet/C++ 컴파일러 회피)
DBeaver 등 GUI 툴로 housing.db 파일 직접 열어서 확인 가능.

테이블:
  users                  - 회원 (이메일/비밀번호 + 카카오 OAuth)
  user_profile           - 추가 사용자 프로필
  checklist_items        - 이사 체크리스트
  search_conditions      - 저장된 검색조건
  recommendation_history - 추천 이력
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "housing.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cur, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ── users ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE,
            password    TEXT,
            birth_date  TEXT,                                    -- YYYY-MM-DD
            gender      TEXT,                                    -- 'M'/'F'
            kakao_id    TEXT UNIQUE,
            nickname    TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    # 기존 테이블 마이그레이션
    if not _column_exists(cur, "users", "kakao_id"):
        cur.execute("ALTER TABLE users ADD COLUMN kakao_id TEXT")
    if not _column_exists(cur, "users", "updated_at"):
        cur.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")

    # ── user_profile ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER NOT NULL REFERENCES users(id),
            employment_status TEXT,
            education_level   TEXT,
            marriage_status   TEXT,
            has_own_house     INTEGER DEFAULT 0,
            income_range      TEXT,
            asset_range       TEXT,
            last_updated      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── checklist_items ───────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            content     TEXT,
            is_checked  INTEGER DEFAULT 0,                       -- 0=미완료, 1=완료
            is_default  INTEGER DEFAULT 0,                       -- 0=사용자, 1=기본
            category    TEXT,                                    -- 이사전/이사당일/이사후
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── search_conditions ─────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_conditions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            workplace       TEXT,
            transport       TEXT,
            contract_type   TEXT,
            deposit         INTEGER,
            monthly_rent    INTEGER,
            commute_time    INTEGER,
            preferred_area  TEXT,
            departure_time  TEXT,
            arrival_time    TEXT,
            house_type      TEXT,
            priority        TEXT,
            amenities       TEXT,
            youth_policy    INTEGER,
            age             INTEGER,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── recommendation_history ────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            workplace     TEXT,
            contract_type TEXT,
            budget        TEXT,
            commute_time  INTEGER,
            result_count  INTEGER,
            top_result    TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] 초기화 완료: {DB_PATH}")
