from pydantic import BaseModel


class EmailBody(BaseModel):
    content: str
    contentType: str


class Email(BaseModel):
    id: str
    conversation_id: str
    subject: str
    sender: str
    recipient: list[str]
    body: EmailBody
    hasAttachments: bool
    attachment_urls: list[str]
