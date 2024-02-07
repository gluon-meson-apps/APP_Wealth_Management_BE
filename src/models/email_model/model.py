from datetime import datetime

from pydantic import BaseModel


class EmailBody(BaseModel):
    content: str
    content_type: str


class EmailSender(BaseModel):
    address: str
    name: str


class Email(BaseModel):
    id: str
    conversation_id: str
    subject: str
    sender: EmailSender
    body: EmailBody
    has_attachments: bool
    attachment_urls: list[str]
    received_date_time: datetime


class EmailAttachment(BaseModel):
    name: str
    content_type: str
    bytes: str
