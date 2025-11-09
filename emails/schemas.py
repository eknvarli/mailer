from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EmailBase(BaseModel):
    sender: str
    recipient: str
    subject: Optional[str]
    body: Optional[str]

class EmailCreate(EmailBase):
    pass

class EmailRead(EmailBase):
    id: int
    received_at: datetime
    is_read: bool

    class Config:
        orm_mode = True
