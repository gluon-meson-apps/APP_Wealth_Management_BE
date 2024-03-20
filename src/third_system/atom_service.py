import base64
import enum
import json
import os

import aiohttp
from loguru import logger


def get_current_user(user_id="email_user"):
    user_info = {"sub": user_id, "realm_access": {"roles": ["user"]}}
    return base64.b64encode(json.dumps(user_info).encode("utf-8"))


class DownstreamMessageFromEnum(str, enum.Enum):
    AI = "ai"
    HUMAN = "human"


class AtomService:
    def __init__(self):
        self.app_id = os.getenv("GLUON_MESON_ATOM_APP_ID")
        self.api_url = os.getenv("GLUON_MESON_ATOM_API_URL")
        if not self.app_id:
            raise ValueError("GLUON_MESON_ATOM_APP_ID is not set")
        if not self.api_url:
            raise ValueError("GLUON_MESON_ATOM_API_URL is not set")

    async def create_message(
        self, conversation_id: str, user_id: str, message: str, message_from: DownstreamMessageFromEnum
    ):
        async with aiohttp.ClientSession() as session:
            try:
                data = {"message": message, "message_type": "email", "message_from": message_from}
                async with session.post(
                    f"{self.api_url}/apps/{self.app_id}/conversations/{conversation_id}/messages",
                    headers={"x-userinfo": get_current_user(user_id), "Content-Type": "application/json"},
                    data=data,
                    ssl=False,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            except Exception as err:
                logger.error(f"Error to create atom message: {err}")
                raise err
