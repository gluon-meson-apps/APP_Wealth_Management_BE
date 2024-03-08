import asyncio
import base64
import os
import urllib.parse
from typing import Union

import aiohttp
from aiohttp import ClientResponseError
from loguru import logger
from tenacity import retry, wait_random_exponential, stop_after_attempt

from action.base import Attachment
from models.email_model.model import Email, EmailBody, EmailSender
from utils.common import get_value_or_default_from_dict, async_parse_json_response


def parse_email(value: dict) -> Email:
    body_value = value.get("body", {})
    sender_value = value.get("sender", {}).get("emailAddress", {})
    body = EmailBody(content=body_value.get("content"), content_type=body_value.get("contentType"))
    email_sender = EmailSender(address=sender_value.get("address"), name=sender_value.get("name"))
    return Email(
        body=body,
        id=value.get("id"),
        conversation_id=value.get("conversationId"),
        subject=value.get("subject"),
        sender=email_sender,
        has_attachments=value.get("hasAttachments"),
        received_date_time=value.get("receivedDateTime"),
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
        self.access_token = get_value_or_default_from_dict(os.environ, "GRAPH_API_ACCESS_TOKEN", "")
        self.config = {
            "client_id": get_value_or_default_from_dict(os.environ, "GRAPH_API_CLIENT_ID", ""),
            "client_secret": get_value_or_default_from_dict(os.environ, "GRAPH_API_CLIENT_SECRET", ""),
            "tenant_id": get_value_or_default_from_dict(os.environ, "GRAPH_API_TENANT_ID", ""),
            "user_id": urllib.parse.quote(get_value_or_default_from_dict(os.environ, "GRAPH_API_USER_ID", "")),
        }
        self.login_endpoint = get_value_or_default_from_dict(os.environ, "GRAPH_API_LOGIN_ENDPOINT", "")
        self.mail_endpoint = get_value_or_default_from_dict(os.environ, "GRAPH_API_MAIL_ENDPOINT", "")
        self.user_api_endpoint = (
            f'{self.mail_endpoint}/v1.0/users/{self.config["user_id"]}'
            if not self.access_token
            else f"{self.mail_endpoint}/v1.0/me"
        )

    def __await__(self):
        return self._init_tokens__().__await__()

    async def _init_tokens__(self):
        if not self.access_token:
            self.access_token = await self.get_access_token()
        self.inbox_folder_id, self.archive_folder_id = await self.list_folders()
        return self

    async def get_access_token(self) -> str:
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "scope": "https://graph.microsoft.com/.default",
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f'{self.login_endpoint}/{self.config["tenant_id"]}/oauth2/v2.0/token',
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    response.raise_for_status()
                    result = await async_parse_json_response(response)
                    return result["access_token"] if "access_token" in result else ""
            except Exception as err:
                logger.error(f"Other error occurred: {err}")
                raise EmailHandlingFailedException(str(err), "GET_TOKEN_FAILED")

    async def refresh_access_token(self):
        self.access_token = await self.get_access_token()

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    async def call_graph_api(self, endpoint: str, method: str = "GET", data: dict = None, **kwargs):
        headers = {"Authorization": "Bearer " + self.access_token}
        extra_headers = kwargs.get("extra_headers", {})
        headers.update(extra_headers)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, headers=headers, json=data) if method == "POST" else session.get(
                    endpoint, headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await async_parse_json_response(response) if response.status in [200, 201] else {}
                    return data["value"] if data and "value" in data else data
            except ClientResponseError as http_err:
                if http_err.status == 401:
                    await self.refresh_access_token()
                    raise TokenExpiredException()
                else:
                    logger.error(f"HTTP error occurred: {http_err}")
                    raise EmailHandlingFailedException(http_err.message, "CALL_API_FAILED")
            except Exception as err:
                logger.error(f"Other error occurred: {err}")
                raise EmailHandlingFailedException(str(err), "CALL_API_FAILED")

    async def list_folders(self):
        data = await self.call_graph_api(f"{self.user_api_endpoint}/mailFolders")
        inbox_folder = next(filter(lambda v: v.get("displayName") in ["收件箱", "Inbox"], data), None) if data else None
        archive_folder = (
            next(filter(lambda v: v.get("displayName") in ["存档", "Archive"], data), None) if data else None
        )
        return inbox_folder.get("id") if inbox_folder else "", archive_folder.get("id") if archive_folder else ""

    async def get_first_inbox_message(self) -> Union[Email, None]:
        fields_query = "$select=id,conversationId,subject,sender,body,hasAttachments,receivedDateTime"
        order_query = "$orderby=receivedDateTime asc"
        endpoint = (
            f"{self.user_api_endpoint}/mailFolders/{self.inbox_folder_id}/messages?{fields_query}&{order_query}&$top=1"
        )
        data = await self.call_graph_api(endpoint, extra_headers={"Prefer": 'outlook.body-content-type="text"'})
        first_message = next(iter(data), None) if data else None
        if first_message and isinstance(first_message, dict):
            parsed_email = parse_email(first_message)
            logger.info(f"Email {parsed_email.id} with {parsed_email.subject} received.")
            if parsed_email.body.content:
                return parsed_email
            else:
                logger.info(f"Email {parsed_email.subject} has no content, archiving it.")
                await self.archive_email(parsed_email)
                return None
        if first_message:
            logger.error(f"Email {first_message} is not valid.")
        return None

    async def list_attachments(self, message_id) -> list[Attachment]:
        endpoint = f"{self.user_api_endpoint}/messages/{message_id}/attachments"
        data = await self.call_graph_api(endpoint)
        return [
            Attachment(
                name=a["name"], path="", contents=base64.b64decode(a["contentBytes"]), content_type=a["contentType"]
            )
            for a in data
            if a and a.get("contentBytes")
        ]

    async def upload_email_attachments(self, email_id: str, attachments: list[Attachment] = None):
        endpoint = f"{self.user_api_endpoint}/messages/{email_id}/attachments"
        if attachments:
            tasks = [
                self.call_graph_api(
                    endpoint,
                    method="POST",
                    data={
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": a.name,
                        "contentBytes": base64.b64encode(a.contents).decode(),
                        "contentType": a.content_type,
                    },
                    extra_headers={"Content-Type": "application/json"},
                )
                for a in attachments
            ]
            await asyncio.gather(*tasks)
            logger.info(f"Upload email attachments for {email_id} successfully.")
        else:
            logger.info(f"No attachments to upload for {email_id}.")

    async def reply_email(self, email: Email, answer: str, attachments: list[Attachment] = None):
        draft_email = await self.call_graph_api(
            f"{self.user_api_endpoint}/messages/{email.id}/createReply",
            method="POST",
            data={
                "comment": answer.replace("\n", "<br>"),
            },
            extra_headers={"Content-Type": "application/json"},
        )
        draft_email_id = draft_email["id"] if draft_email and "id" in draft_email else ""
        if draft_email_id:
            await self.upload_email_attachments(draft_email_id, attachments)
            await self.call_graph_api(
                endpoint=f"{self.user_api_endpoint}/messages/{draft_email_id}/send",
                method="POST",
            )
            logger.info(f"Reply email to {email.sender.address} successfully.")
            await self.archive_email(email)
        else:
            logger.error(f"Reply email to {email.sender.address} failed.")
            raise EmailHandlingFailedException("Reply email failed.", "REPLY_EMAIL_FAILED")

    async def archive_email(self, email: Email):
        endpoint = f"{self.user_api_endpoint}/mailFolders/{self.inbox_folder_id}/messages/{email.id}/move"
        await self.call_graph_api(
            endpoint,
            method="POST",
            data={
                "destinationId": self.archive_folder_id,
            },
        )
        logger.info("Archive email successfully.")
