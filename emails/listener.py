import asyncio
import logging
from email import message_from_bytes
from email.header import decode_header
from typing import Dict
import aioimaplib
from sqlalchemy.ext.asyncio import AsyncSession
from core.crypto import decrypt_secret
from emails.models import Email as EmailModel
from core.database import async_session
from auth.models import User

logger = logging.getLogger("emails.listener")
LISTENER_TASKS: Dict[int, asyncio.Task] = {}

def _decode_header_value(h):
    if not h:
        return ""
    parts = decode_header(h)
    out = []
    for val, enc in parts:
        if isinstance(val, bytes):
            out.append(val.decode(enc or "utf-8", errors="ignore"))
        else:
            out.append(val)
    return "".join(out)

async def _store_email(db: AsyncSession, user_id: int, sender: str, recipient: str, subject: str, body: str):
    e = EmailModel(user_id=user_id, sender=sender, recipient=recipient, subject=subject, body=body)
    db.add(e)
    await db.commit()
    await db.refresh(e)
    logger.info("Stored email id=%s for user=%s", e.id, user_id)
    return e

async def _fetch_and_store_by_id(imap_client: aioimaplib.IMAP4_SSL, msg_id: bytes, db: AsyncSession, user_id: int):
    ok, parts = await imap_client.fetch(msg_id, "(RFC822)")
    raw = None
    for p in parts:
        if isinstance(p, tuple) and len(p) >= 2:
            raw = p[1]
            break
    if not raw:
        return
    msg = message_from_bytes(raw)
    subject = _decode_header_value(msg.get("Subject"))
    sender = msg.get("From")
    to = msg.get("To")
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get('Content-Disposition')
            if ctype == 'text/plain' and disp is None:
                body = part.get_payload(decode=True).decode(errors='ignore')
                break
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    await _store_email(db, user_id, sender or "", to or "", subject or "", body or "")

async def _polling_loop_for_user(user: User, stop_event: asyncio.Event, interval: int = 30):
    """Polling-based mail listener"""
    password = decrypt_secret(user.email_password_encrypted) if getattr(user, "email_password_encrypted", None) else user.email_password
    imap_host = user.email_imap_host or "imap."+user.email.split("@",1)[1]
    imap_port = user.email_imap_port or 993

    async with async_session() as db:
        client = aioimaplib.IMAP4_SSL(host=imap_host, port=imap_port)
        await client.wait_hello_from_server()
        await client.login(user.email, password)
        await client.select("INBOX")
        logger.info("IMAP polling started for user %s", user.id)

        try:
            while not stop_event.is_set():
                ok, data = await client.search("UNSEEN")
                if ok == 'OK' and data and data[0]:
                    ids = data[0].split()
                    for mid in ids:
                        await _fetch_and_store_by_id(client, mid, db, user.id)
                await asyncio.sleep(interval)
        finally:
            try:
                await client.logout()
            except Exception:
                pass
            logger.info("IMAP polling stopped for user %s", user.id)

async def start_listener_for_user(user: User):
    if user.id in LISTENER_TASKS and not LISTENER_TASKS[user.id].done():
        return
    stop_event = asyncio.Event()
    task = asyncio.create_task(_polling_loop_for_user(user, stop_event))
    task._stop_event = stop_event
    LISTENER_TASKS[user.id] = task
    logger.info("Started polling listener for user %s", user.id)

async def stop_listener_for_user(user_id: int):
    task = LISTENER_TASKS.get(user_id)
    if not task:
        return
    if hasattr(task, "_stop_event"):
        task._stop_event.set()
    await asyncio.wait_for(task, timeout=30)
    LISTENER_TASKS.pop(user_id, None)
    logger.info("Stopped polling listener for user %s", user_id)
