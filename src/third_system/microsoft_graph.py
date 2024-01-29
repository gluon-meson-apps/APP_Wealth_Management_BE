import os
import urllib.parse

import requests

from models.email_model.model import Email, EmailBody, EmailSender
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
        response = requests.get(endpoint, headers=headers)
        data = response.json()
        if response.ok:
            values = data["value"] if "value" in data and data["value"] else []
            return [parse_email(v) for v in values]
        elif response.status_code == 401 and data["error"]["code"] == "InvalidAuthenticationToken":
            self.refresh_access_token()
            return self.get_new_emails()
        else:
            raise Exception("Getting email failed")

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
            return self.list_attachments()
        else:
            raise Exception("Getting email attachments failed")
