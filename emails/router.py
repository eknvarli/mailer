from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from auth.services import decode_token
from core.database import get_db
from auth import services as auth_services
from auth.models import User
from core.crypto import decrypt_secret
import asyncio
from emails.services import fetch_emails
from emails.poller import EmailPoller
from auth.dependencies import get_current_user

from emails.analysis import MailAnalyzer

analyzer = MailAnalyzer('training_data.json')

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


class AnalysisResult(BaseModel):
    category: str
    subcategory: str
    priority: str
    sentiment: str
    urgency: str
    department: str
    action_required: str
    response_template: str
    confidence_score: float


class AnalyzedEmail(BaseModel):
    subject: Optional[str]
    sender: Optional[str]
    to: Optional[str]
    date: Optional[str]
    body: Optional[str]
    analysis: AnalysisResult


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
async def start_polling(config: dict, user=Depends(get_current_user)):
    from emails.poller import EmailPoller
    poller = EmailPoller(config["server"], config["email"], config["password"], config["interval"])
    poller.start()
    pollers[config["email"]] = poller
    return {"status": "polling started"}


@router.get("/listen")
async def listen_emails(email: str, user=Depends(get_current_user)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started"}
    return poller.get_emails()


@router.get("/analyze")
async def analyze_emails(email: str, user=Depends(get_current_user)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started"}

    emails = poller.get_emails()
    analyzed = []

    for mail in emails:
        analysis_result = analyzer.predict_detailed(mail["body"])

        analyzed.append({
            "subject": mail.get("subject"),
            "sender": mail.get("sender") or mail.get("from"),
            "to": mail.get("to"),
            "date": mail.get("date"),
            "body": mail.get("body"),
            "analysis": analysis_result
        })

    return analyzed


@router.get("/analyze-single")
async def analyze_single_email(text: str, user=Depends(get_current_user)):
    analysis_result = analyzer.predict_detailed(text)
    return {
        "text": text,
        "analysis": analysis_result
    }


@router.get("/stats")
async def get_analysis_stats(email: str, user=Depends(get_current_user)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started"}

    emails = poller.get_emails()
    stats = {
        "total_emails": len(emails),
        "categories": {},
        "priorities": {},
        "sentiments": {},
        "departments": {},
        "urgencies": {}
    }

    for mail in emails:
        analysis_result = analyzer.predict_detailed(mail["body"])

        category = analysis_result["category"]
        priority = analysis_result["priority"]
        sentiment = analysis_result["sentiment"]
        department = analysis_result["department"]
        urgency = analysis_result["urgency"]

        stats["categories"][category] = stats["categories"].get(category, 0) + 1
        stats["priorities"][priority] = stats["priorities"].get(priority, 0) + 1
        stats["sentiments"][sentiment] = stats["sentiments"].get(sentiment, 0) + 1
        stats["departments"][department] = stats["departments"].get(department, 0) + 1
        stats["urgencies"][urgency] = stats["urgencies"].get(urgency, 0) + 1

    return stats


@router.get("/priority-emails")
async def get_priority_emails(email: str, priority: str = "yüksek", user=Depends(get_current_user)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started"}

    emails = poller.get_emails()
    priority_emails = []

    for mail in emails:
        analysis_result = analyzer.predict_detailed(mail["body"])
        if analysis_result["priority"] == priority:
            priority_emails.append({
                "subject": mail.get("subject"),
                "sender": mail.get("sender") or mail.get("from"),
                "date": mail.get("date"),
                "analysis": analysis_result
            })

    return {
        "priority": priority,
        "count": len(priority_emails),
        "emails": priority_emails
    }


@router.get("/department-emails")
async def get_department_emails(email: str, department: str, user=Depends(get_current_user)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started"}

    emails = poller.get_emails()
    department_emails = []

    for mail in emails:
        analysis_result = analyzer.predict_detailed(mail["body"])
        if analysis_result["department"] == department:
            department_emails.append({
                "subject": mail.get("subject"),
                "sender": mail.get("sender") or mail.get("from"),
                "date": mail.get("date"),
                "analysis": analysis_result
            })

    return {
        "department": department,
        "count": len(department_emails),
        "emails": department_emails
    }


@router.get("/debug-emails")
async def debug_emails(email: str, user=Depends(get_current_user)):
    poller = pollers.get(email)
    if not poller:
        return {"status": "poller not started"}

    emails = poller.get_emails()

    if not emails:
        return {"message": "No emails found", "email_structure": "No emails to analyze"}

    first_email_keys = list(emails[0].keys()) if emails else []

    return {
        "total_emails": len(emails),
        "first_email_keys": first_email_keys,
        "sample_email": emails[0] if emails else {}
    }