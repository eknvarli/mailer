from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from auth.services import decode_token
from core.database import get_db
from auth import services as auth_services
from auth.models import User
from core.crypto import decrypt_secret
import asyncio
from emails.services import fetch_emails
from emails.poller import EmailPoller

router = APIRouter(prefix="/mail", tags=["emails"])
pollers = {}

class ListenRequest(BaseModel):
    imap_host: Optional[str] = None
    imap_port: Optional[int] = 993
    limit: Optional[int] = 20

class EmailOut(BaseModel):
    subject: Optional[str]
    sender: Optional[str]
    to: Optional[str]
    date: Optional[str]
    body: Optional[str]

    class Config:
        orm_mode = True

class IMAPConfig(BaseModel):
    server: str
    email: str
    password: str
    interval: int = 60

async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    user_data = decode_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_data

def _get_user_id_from_token_or_401(token: str) -> int:
    payload = auth_services.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return int(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

def _fetch_unseen_sync(imap_host: str, imap_port: int, email_addr: str, password: str, limit: int):
    """Blocking IMAP fetcher using imaplib — to be run in thread via asyncio.to_thread."""
    import imaplib, email
    from email.header import decode_header

    def _decode(h):
        if not h:
            return ""
        parts = decode_header(h)
        out = []
        for v, enc in parts:
            if isinstance(v, bytes):
                out.append(v.decode(enc or "utf-8", errors="ignore"))
            else:
                out.append(v)
        return "".join(out)

    M = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=30)
    try:
        M.login(email_addr, password)
    except imaplib.IMAP4.error as e:
        M.logout()
        raise RuntimeError(f"IMAP login failed: {e}")
    M.select("INBOX")
    typ, data = M.search(None, "UNSEEN")
    out = []
    if typ == "OK" and data and data[0]:
        ids = data[0].split()
        ids = ids[-limit:]
        for msgid in reversed(ids):
            res, msg_data = M.fetch(msgid, "(RFC822)")
            if res != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = _decode(msg.get("Subject"))
            sender = msg.get("From")
            to = msg.get("To")
            date = msg.get("Date")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    disp = str(part.get("Content-Disposition"))
                    if ctype == "text/plain" and "attachment" not in disp:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
            out.append({
                "subject": subject,
                "sender": sender,
                "to": to,
                "date": date,
                "body": body
            })
    try:
        M.logout()
    except Exception:
        pass
    return out

@router.post("/start")
async def start_polling(config: IMAPConfig, user=Depends(verify_token)):
    poller = EmailPoller(config.server, config.email, config.password, config.interval)
    poller.start()
    pollers[config.email] = poller
    return {"status": "polling started"}

@router.get("/listen")
async def listen_emails(email: str, user=Depends(verify_token)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started for this email"}
    return poller.get_emails()
