from pydantic import BaseModel

class Attachment(BaseModel):
    name: str
    contentBytes: str

class Email(BaseModel):
    subject: str
    sender: str
    recipient: list[str]
    body: str
    hasAttachments: bool
    attachments: Attachment = None