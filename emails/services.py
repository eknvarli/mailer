from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from emails.models import Email
import imaplib
import email
from email.header import decode_header
from core.crypto import decrypt_secret
from auth.models import User
import asyncio

class MailListener:
    def __init__(self, imap_server: str, email_address: str, encrypted_password: str):
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = decrypt_secret(encrypted_password)
        self.conn = None

    def connect(self):
        self.conn = imaplib.IMAP4_SSL(self.imap_server)
        self.conn.login(self.email_address, self.password)
        self.conn.select("INBOX")

    def fetch_unseen(self):
        status, messages = self.conn.search(None, 'UNSEEN')
        emails = []
        if status == "OK":
            for num in messages[0].split():
                res, msg_data = self.conn.fetch(num, '(RFC822)')
                if res != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                else:
                    body = msg.get_payload(decode=True).decode()
                emails.append({
                    "subject": subject,
                    "body": body,
                    "from": msg.get("From")
                })
        return emails


async def get_user_emails(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Email)
        .where(Email.user_id == user_id)
        .order_by(Email.received_at.desc())
    )
    emails = result.scalars().all()
    return emails

async def fetch_emails(server: str, email_user: str, email_pass: str):
    emails = []

    try:
        imap = imaplib.IMAP4_SSL(server)
        imap.login(email_user, email_pass)
        imap.select("INBOX")

        status, messages = imap.search(None, "ALL")
        mail_ids = messages[0].split()

        for mail_id in mail_ids[-10:]:
            status, msg_data = imap.fetch(mail_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    from_ = msg.get("From")
                    date_ = msg.get("Date")
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()

                    emails.append({
                        "subject": subject,
                        "from": from_,
                        "body": body,
                        "date": date_
                    })
        imap.logout()
    except Exception as e:
        print(f"Polling hatası: {e}")

    return emails