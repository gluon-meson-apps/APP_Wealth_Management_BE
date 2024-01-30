import logging
import os
import urllib.parse
import uuid
from datetime import datetime

import requests
from loguru import logger

from models.email_model.model import Email, EmailBody, EmailSender, EmailAttachment
from utils.utils import get_value_or_default_from_dict


def parse_email(value: dict) -> Email:
    body_value = value["body"] if "body" in value and value["body"] else {}
    sender_value = value["sender"] if "sender" in value and value["sender"] else {}
    body = EmailBody(content=body_value["content"], content_type=body_value["contentType"])
    email_sender = EmailSender(
        address=sender_value["emailAddress"]["address"], name=sender_value["emailAddress"]["name"]
    )
    return Email(
        body=body,
        id=value["id"],
        conversation_id=value["conversationId"],
        subject=value["subject"],
        sender=email_sender,
        has_attachments=value["hasAttachments"],
        received_date_time=value["receivedDateTime"],
        attachment_urls=[],
    )


class GettingEmailFailedException(Exception):
    def __init__(self, message: str, error_code):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class Graph:
    access_token: str

    def __init__(self):
        self.config = {
            "client_id": get_value_or_default_from_dict(os.environ, "GRAPH_API_CLIENT_ID", ""),
            "client_secret": get_value_or_default_from_dict(os.environ, "GRAPH_API_CLIENT_SECRET", ""),
            "tenant_id": get_value_or_default_from_dict(os.environ, "GRAPH_API_TENANT_ID", ""),
            "user_id": urllib.parse.quote(get_value_or_default_from_dict(os.environ, "GRAPH_API_USER_ID", "")),
        }
        self.get_access_token()

    def get_access_token(self, grant_type="client_credentials"):
        data = {
            "grant_type": grant_type,
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "scope": "https://graph.microsoft.com/.default",
        }
        if grant_type == "refresh_token":
            data["refresh_token"] = self.config["access_token"]
        response = requests.post(
            f'https://login.microsoftonline.com/{self.config["tenant_id"]}/oauth2/v2.0/token',
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.ok:
            result = response.json()
            if "access_token" in result:
                self.access_token = result["access_token"]
        else:
            raise Exception("Get MS graph token failed.")

    def refresh_access_token(self):
        self.get_access_token(grant_type="refresh_token")

    def get_new_emails(self, received_date_time=None) -> list[Email]:
        fields_query = "$select=id,conversationId,subject,sender,body,hasAttachments,receivedDateTime"
        filter_query = f"&$filter=receivedDateTime ge {received_date_time}" if received_date_time else ""
        endpoint = (
            f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/messages?{fields_query}{filter_query}'
        )
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = requests.get(endpoint, headers=headers)
            data = response.json()
            if response.ok:
                values = data["value"] if "value" in data and data["value"] else []
                return [parse_email(v) for v in values]
            elif response.status_code == 401 and data["error"]["code"] == "InvalidAuthenticationToken":
                self.refresh_access_token()
                return self.get_new_emails(received_date_time)
            else:
                raise GettingEmailFailedException(response.text, response.status_code)
        except GettingEmailFailedException as e:
            logging.warning(f"[{str(e.error_code)}]: {e.message}")
            return [Email(
                id=str(uuid.uuid4()),
                conversation_id=str(uuid.uuid4()),
                subject="Sample Email For Testing",
                sender=EmailSender(
                    address="test@example.com",
                    name="john",
                ),
                body=EmailBody(
                    content_type="text/plain",
                    content="This is a sample email body",
                ),
                has_attachments=False,
                attachment_urls=[],
                received_date_time=datetime.utcnow()
            )]

    def list_attachments(self, message_id):
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/messages/{message_id}/attachments'
        headers = {"Authorization": "Bearer " + self.access_token}
        response = requests.get(endpoint, headers=headers)
        data = response.json()
        if response.ok:
            values = data["value"] if "value" in data and data["value"] else []
            return [v for v in values if "contentBytes" in v and v["contentBytes"]]
        elif response.status_code == 401 and data["error"]["code"] == "InvalidAuthenticationToken":
            self.refresh_access_token()
            return self.list_attachments(message_id)
        else:
            raise Exception("Getting email attachments failed")

    def send_email(self, email: Email, answer: str, attachments: list[EmailAttachment] = None):
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/sendMail'
        headers = {"Authorization": "Bearer " + self.access_token}
        message = {
            "subject": f"[TB Guru Reply] {email.subject}",
            "body": {"contentType": "Text", "content": answer},
            "toRecipients": [{"emailAddress": {"address": email.sender.address}}],
        }
        if attachments:
            message["attachments"] = [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": a.name,
                    "contentType": a.type,
                    "contentBytes": a.bytes,
                }
                for a in attachments
            ]
        response = requests.post(
            endpoint,
            headers=headers,
            json={
                "message": message,
                "saveToSentItems": "true",
            },
        )
        if response.ok:
            logger.info(f"Send email to {email.sender.address} successfully.")
            return
        elif response.status_code == 401:
            message = response.json()
            if message["error"]["code"] == "InvalidAuthenticationToken":
                self.refresh_access_token()
                self.send_email(email, answer)
        else:
            logger.error(f"Send email to {email.sender.address} failed.")
            raise Exception("Sending email failed")
