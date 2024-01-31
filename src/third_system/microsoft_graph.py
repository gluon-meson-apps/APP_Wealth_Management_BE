import logging
import os
import urllib.parse
from typing import Union

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


class EmailHandlingFailedException(Exception):
    def __init__(self, message: str, error_type: str):
        self.message = message
        self.error_type = error_type
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
        self.inbox_folder_id, self.archive_folder_id = self.list_folders()
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

    def list_folders(self):
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/mailFolders'
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = requests.get(endpoint, headers=headers)
            data = response.json()
            if response.ok:
                values = data["value"] if "value" in data and data["value"] else []
                inbox_folder = next(filter(values, lambda v: v.get("displayName") in ["收件箱", "Inbox"]), None)
                archive_folder = next(filter(values, lambda v: v.get("displayName") in ["存档", "Archive"]), None)
                return inbox_folder.get("id") if inbox_folder else "", archive_folder.get(
                    "id"
                ) if archive_folder else ""
            elif response.status_code == 401 and data["error"]["code"] == "InvalidAuthenticationToken":
                self.refresh_access_token()
                return self.list_folders()
            else:
                raise EmailHandlingFailedException(response.text, "GETTING_FOLDERS_FAILED")
        except EmailHandlingFailedException as e:
            logging.warning(f"[{str(e.error_type)}]: {e.message}")
            return "", ""

    def get_first_inbox_message(self, received_date_time=None) -> Union[Email, None]:
        fields_query = "$select=id,conversationId,subject,sender,body,hasAttachments,receivedDateTime"
        order_query = "$orderby=receivedDateTime asc"
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/mailFolders/{self.inbox_folder_id}/messages?{fields_query}&{order_query}&$top=1'
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = requests.get(endpoint, headers=headers)
            data = response.json()
            if response.ok:
                values = data["value"] if "value" in data and data["value"] else []
                first_message = next(iter(values), None)
                return parse_email(first_message) if first_message else None
            elif response.status_code == 401 and data["error"]["code"] == "InvalidAuthenticationToken":
                self.refresh_access_token()
                return self.get_first_inbox_message(received_date_time)
            else:
                raise EmailHandlingFailedException(response.text, "GETTING_NEW_EMAIL_FAILED")
        except EmailHandlingFailedException as e:
            logging.warning(f"[{str(e.error_type)}]: {e.message}")
            return None

    def list_attachments(self, message_id):
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/messages/{message_id}/attachments'
        headers = {"Authorization": "Bearer " + self.access_token}

        try:
            response = requests.get(endpoint, headers=headers)
            data = response.json()
            if response.ok:
                values = data["value"] if "value" in data and data["value"] else []
                return [v for v in values if "contentBytes" in v and v["contentBytes"]]
            elif response.status_code == 401 and data["error"]["code"] == "InvalidAuthenticationToken":
                self.refresh_access_token()
                return self.list_attachments(message_id)
            else:
                raise EmailHandlingFailedException(response.text, "LIST_ATTACHMENTS_FAILED")
        except EmailHandlingFailedException as e:
            logging.warning(f"[{str(e.error_type)}]: {e.message}")
            return []

    def send_email(self, email: Email, answer: str, attachments: list[EmailAttachment] = None):
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}/sendMail'
        headers = {"Authorization": "Bearer " + self.access_token}
        message = {
            "subject": f"[TB Guru Reply] {email.subject}",
            "body": {"contentType": "html", "content": answer},
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
            message["hasAttachments"] = True

        try:
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
                    self.send_email(email, answer, attachments)
            else:
                logger.error(f"Send email to {email.sender.address} failed.")
                raise EmailHandlingFailedException(response.text, "SEND_EMAIL_FAILED")
        except EmailHandlingFailedException as e:
            logging.warning(f"[{str(e.error_type)}]: {e.message}")
            return
