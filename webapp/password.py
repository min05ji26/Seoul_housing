"""
webapp/password.py
──────────────────
비밀번호 재설정 (이메일 인증코드 방식)

Gmail SMTP 사용 → .env에 EMAIL_ADDRESS / EMAIL_PASSWORD 필요
- EMAIL_PASSWORD는 Gmail 앱 비밀번호 (https://myaccount.google.com/apppasswords)

엔드포인트:
  POST /password/send-code      - 이메일로 6자리 코드 발송
  POST /password/verify-code    - 코드 확인
  POST /password/reset-password - 비밀번호 변경
"""
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext

from webapp.database import get_conn

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 메모리에 (이메일 → {code, expire}) 저장. 운영 환경에서는 Redis 권장.
_reset_codes: dict = {}
CODE_TTL_MINUTES = 10

EMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def _send_email(to_email: str, code: str):
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_email
    msg["Subject"] = "[집찾봇] 비밀번호 재설정 코드"

    body = f"""안녕하세요!

비밀번호 재설정 코드입니다:

【 {code} 】

코드는 10분간 유효합니다.
본인이 요청하지 않았다면 이 메일을 무시해주세요.
"""
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


# ── 스키마 ───────────────────────────────────────────────
class EmailRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code:  str


class ResetPasswordRequest(BaseModel):
    email:        str
    code:         str
    new_password: str


# ── 코드 발송 ───────────────────────────────────────────
@router.post("/send-code")
def send_reset_code(req: EmailRequest):
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="존재하지 않는 이메일입니다")

    code = "".join(random.choices(string.digits, k=6))
    _reset_codes[req.email] = {
        "code":   code,
        "expire": datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES),
    }

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        # 개발용: 메일 미설정 시 콘솔에 코드 출력
        print(f"[비밀번호재설정] {req.email} 코드: {code} (이메일 설정 X — 개발모드)")
        return {"message": "(개발모드) 인증 코드를 콘솔에 출력했습니다"}

    try:
        _send_email(req.email, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 전송 실패: {e}")
    return {"message": "인증 코드를 이메일로 발송했습니다"}


# ── 코드 확인 ───────────────────────────────────────────
@router.post("/verify-code")
def verify_code(req: VerifyCodeRequest):
    rec = _reset_codes.get(req.email)
    if not rec:
        raise HTTPException(status_code=400, detail="코드가 발급되지 않았습니다")
    if rec["expire"] < datetime.utcnow():
        del _reset_codes[req.email]
        raise HTTPException(status_code=400, detail="코드가 만료되었습니다")
    if rec["code"] != req.code:
        raise HTTPException(status_code=400, detail="코드가 올바르지 않습니다")
    return {"message": "코드 확인 완료"}


# ── 비밀번호 재설정 ─────────────────────────────────────
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    rec = _reset_codes.get(req.email)
    if not rec or rec["code"] != req.code:
        raise HTTPException(status_code=400, detail="코드가 올바르지 않습니다")
    if rec["expire"] < datetime.utcnow():
        del _reset_codes[req.email]
        raise HTTPException(status_code=400, detail="코드가 만료되었습니다")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")

    hashed = pwd_context.hash(req.new_password)
    conn = get_conn()
    try:
        conn.execute("UPDATE users SET password=? WHERE email=?", (hashed, req.email))
        conn.commit()
    finally:
        conn.close()

    del _reset_codes[req.email]
    return {"message": "비밀번호가 변경되었습니다"}
