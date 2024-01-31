import os
import urllib.parse
from typing import Union

import requests
from loguru import logger
from requests import HTTPError

from models.email_model.model import Email, EmailBody, EmailSender, EmailAttachment
from utils.utils import get_value_or_default_from_dict, parse_json_response


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


class TokenExpiredException(Exception):
    def __init__(self):
        self.message = "Token expired"
        self.error_type = "TOKEN_EXPIRED"
        super().__init__(self.message)


class Graph:
    def __init__(self):
        self.config = {
            "client_id": get_value_or_default_from_dict(os.environ, "GRAPH_API_CLIENT_ID", ""),
            "client_secret": get_value_or_default_from_dict(os.environ, "GRAPH_API_CLIENT_SECRET", ""),
            "tenant_id": get_value_or_default_from_dict(os.environ, "GRAPH_API_TENANT_ID", ""),
            "user_id": urllib.parse.quote(get_value_or_default_from_dict(os.environ, "GRAPH_API_USER_ID", "")),
        }
        self.user_api_endpoint = f'https://graph.microsoft.com/v1.0/users/{self.config["user_id"]}'
        self.access_token = self.get_access_token()
        self.inbox_folder_id, self.archive_folder_id = self.list_folders()

    def get_access_token(self) -> str:
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "scope": "https://graph.microsoft.com/.default",
            }
            response = requests.post(
                f'https://login.microsoftonline.com/{self.config["tenant_id"]}/oauth2/v2.0/token',
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            result = response.json()
            return result["access_token"] if "access_token" in result else ""
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "GET_TOKEN_FAILED")

    def refresh_access_token(self):
        self.access_token = self.get_access_token()

    def check_token_expired(self, response):
        data = parse_json_response(response)
        result = response.status_code == 401 and data.get("error", {}).get("code") == "InvalidAuthenticationToken"
        if result:
            self.refresh_access_token()
        return result

    def call_graph_api(self, endpoint: str, method: str = "GET", data: dict = None):
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = (
                requests.get(endpoint, headers=headers)
                if method == "GET"
                else requests.post(endpoint, headers=headers, json=data)
            )
            response.raise_for_status()
            data = parse_json_response(response) if response.status_code == 200 else {}
            return data["value"] if "value" in data and data["value"] else []
        except HTTPError as http_err:
            if self.check_token_expired(http_err.response):
                raise TokenExpiredException()
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise EmailHandlingFailedException(http_err.response.text, "CALL_API_FAILED")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "CALL_API_FAILED")

    def list_folders(self):
        try:
            data = self.call_graph_api(f"{self.user_api_endpoint}/mailFolders")
            inbox_folder = next(filter(lambda v: v.get("displayName") in ["收件箱", "Inbox"], data), None)
            archive_folder = next(filter(lambda v: v.get("displayName") in ["存档", "Archive"], data), None)
            return inbox_folder.get("id") if inbox_folder else "", archive_folder.get("id") if archive_folder else ""
        except TokenExpiredException:
            return self.list_folders()

    def get_first_inbox_message(self) -> Union[Email, None]:
        try:
            fields_query = "$select=id,conversationId,subject,sender,body,hasAttachments,receivedDateTime"
            order_query = "$orderby=receivedDateTime asc"
            endpoint = f"{self.user_api_endpoint}/mailFolders/{self.inbox_folder_id}/messages?{fields_query}&{order_query}&$top=1"
            data = self.call_graph_api(endpoint)
            first_message = next(iter(data), None)
            return parse_email(first_message) if first_message else None
        except TokenExpiredException:
            return self.get_first_inbox_message()

    def list_attachments(self, message_id):
        try:
            endpoint = f"{self.user_api_endpoint}/messages/{message_id}/attachments"
            data = self.call_graph_api(endpoint)
            return [v for v in data if "contentBytes" in v and v["contentBytes"]]
        except TokenExpiredException:
            return self.list_attachments(message_id)

    def send_email(self, email: Email, answer: str, attachments: list[EmailAttachment] = None):
        try:
            endpoint = f"{self.user_api_endpoint}/sendMail"
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

            self.call_graph_api(
                endpoint,
                method="POST",
                data={
                    "message": message,
                    "saveToSentItems": "true",
                },
            )
            logger.info(f"Send email to {email.sender.address} successfully.")
            self.archive_email(email)
        except TokenExpiredException:
            self.send_email(email, answer, attachments)

    def archive_email(self, email: Email):
        try:
            endpoint = f"{self.user_api_endpoint}/mailFolders/{self.inbox_folder_id}/messages/{email.id}/move"
            self.call_graph_api(
                endpoint,
                method="POST",
                data={
                    "destinationId": self.archive_folder_id,
                },
            )
            logger.info("Archive email successfully.")
        except TokenExpiredException:
            self.archive_email(email)
