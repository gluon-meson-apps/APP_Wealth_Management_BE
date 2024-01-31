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

    def get_access_token(self, grant_type="client_credentials") -> str:
        try:
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
            response.raise_for_status()
            result = response.json()
            return result["access_token"] if "access_token" in result else ""
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "GET_TOKEN_FAILED")

    def refresh_access_token(self):
        self.access_token = self.get_access_token(grant_type="refresh_token")

    def check_token_expired(self, response):
        data = parse_json_response(response)
        result = response.status_code == 401 and data.get("error", {}).get("code") == "InvalidAuthenticationToken"
        if result:
            self.refresh_access_token()
        return result

    def list_folders(self):
        endpoint = f"{self.user_api_endpoint}/mailFolders"
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            values = data["value"] if "value" in data and data["value"] else []
            inbox_folder = next(filter(lambda v: v.get("displayName") in ["收件箱", "Inbox"], values), None)
            archive_folder = next(filter(lambda v: v.get("displayName") in ["存档", "Archive"], values), None)
            return inbox_folder.get("id") if inbox_folder else "", archive_folder.get("id") if archive_folder else ""
        except HTTPError as http_err:
            if self.check_token_expired(http_err.response):
                return self.list_folders()
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise EmailHandlingFailedException(http_err.response.text, "LIST_FOLDER_FAILED")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "LIST_FOLDER_FAILED")

    def get_first_inbox_message(self) -> Union[Email, None]:
        fields_query = "$select=id,conversationId,subject,sender,body,hasAttachments,receivedDateTime"
        order_query = "$orderby=receivedDateTime asc"
        endpoint = (
            f"{self.user_api_endpoint}/mailFolders/{self.inbox_folder_id}/messages?{fields_query}&{order_query}&$top=1"
        )
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            values = data["value"] if "value" in data and data["value"] else []
            first_message = next(iter(values), None)
            return parse_email(first_message) if first_message else None
        except HTTPError as http_err:
            if self.check_token_expired(http_err.response):
                return self.get_first_inbox_message()
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise EmailHandlingFailedException(http_err.response.text, "GETTING_NEW_EMAIL_FAILED")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "GETTING_NEW_EMAIL_FAILED")

    def list_attachments(self, message_id):
        endpoint = f"{self.user_api_endpoint}/messages/{message_id}/attachments"
        headers = {"Authorization": "Bearer " + self.access_token}

        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
            values = data["value"] if "value" in data and data["value"] else []
            return [v for v in values if "contentBytes" in v and v["contentBytes"]]
        except HTTPError as http_err:
            if self.check_token_expired(http_err.response):
                return self.list_attachments(message_id)
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise EmailHandlingFailedException(http_err.response.text, "LIST_ATTACHMENTS_FAILED")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "LIST_ATTACHMENTS_FAILED")

    def send_email(self, email: Email, answer: str, attachments: list[EmailAttachment] = None):
        endpoint = f"{self.user_api_endpoint}/sendMail"
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
            response.raise_for_status()
            logger.info(f"Send email to {email.sender.address} successfully.")
            self.archive_email(email)
        except HTTPError as http_err:
            if self.check_token_expired(http_err.response):
                self.send_email(email, answer, attachments)
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise EmailHandlingFailedException(http_err.response.text, "SEND_EMAIL_FAILED")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "SEND_EMAIL_FAILED")

    def archive_email(self, email: Email):
        endpoint = f"{self.user_api_endpoint}/mailFolders/{self.inbox_folder_id}/messages/{email.id}/move"
        headers = {"Authorization": "Bearer " + self.access_token}
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={
                    "destinationId": self.archive_folder_id,
                },
            )
            response.raise_for_status()
            logger.info("Archive email successfully.")
        except HTTPError as http_err:
            if self.check_token_expired(http_err.response):
                self.archive_email(email)
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                raise EmailHandlingFailedException(http_err.response.text, "ARCHIVE_EMAIL_FAILED")
        except Exception as err:
            logger.error(f"Other error occurred: {err}")
            raise EmailHandlingFailedException(str(err), "ARCHIVE_EMAIL_FAILED")
