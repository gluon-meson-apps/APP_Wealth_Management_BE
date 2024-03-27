import asyncio
import base64
import enum
import json
import os
import uuid

import aiohttp
import dotenv
from loguru import logger


def get_current_user(user_id="email_user"):
    user_info = {"sub": user_id, "realm_access": {"roles": ["user"]}}
    return base64.b64encode(json.dumps(user_info).encode("utf-8")).decode("utf-8")


class DownstreamMessageFromEnum(str, enum.Enum):
    AI = "ai"
    HUMAN = "human"


class DownstreamMessageTypeEnum(str, enum.Enum):
    EMAIL = "email"
    UI = "ui"


class AtomService:
    def __init__(self):
        self.app_id = os.getenv("GLUON_MESON_ATOM_APP_ID")
        self.api_url = os.getenv("GLUON_MESON_ATOM_API_URL")
        self.home_url = os.getenv("GLUON_MESON_ATOM_HOMEPAGE_URL")
        if not self.app_id:
            raise ValueError("GLUON_MESON_ATOM_APP_ID is not set")
        if not self.api_url:
            raise ValueError("GLUON_MESON_ATOM_API_URL is not set")
        if not self.home_url:
            raise ValueError("GLUON_MESON_ATOM_HOMEPAGE_URL is not set")

    def generate_feedback_link(self, message_id: str) -> str:
        return f"{self.home_url}/assistants/chat/{self.app_id}/feedback/{message_id}"

    async def create_message(
        self,
        conversation_id: str,
        user_id: str,
        message_from: DownstreamMessageFromEnum,
        message_type: DownstreamMessageTypeEnum,
        message: str = None,
        prompt_message: dict = None,
    ):
        async with aiohttp.ClientSession() as session:
            try:
                data = {
                    "message": message,
                    "message_type": message_type.value,
                    "message_from": message_from.value,
                    "prompt_message": prompt_message,
                }
                async with session.post(
                    f"{self.api_url}/apps/{self.app_id}/conversations/{conversation_id}/downstream_message",
                    headers={"x-userinfo": get_current_user(user_id), "Content-Type": "application/json"},
                    json=data,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            except Exception as err:
                logger.error(f"Error to create atom message: {err}")
                return None

    async def create_human_message(
        self, conversation_id: str, user_id: str, message: str = None, prompt_message: dict = None
    ):
        return await self.create_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message_from=DownstreamMessageFromEnum.HUMAN,
            message_type=DownstreamMessageTypeEnum.EMAIL,
            message=message,
            prompt_message=prompt_message,
        )

    async def create_ai_message(
        self, conversation_id: str, user_id: str, message: str = None, prompt_message: dict = None
    ):
        return await self.create_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message_from=DownstreamMessageFromEnum.AI,
            message_type=DownstreamMessageTypeEnum.EMAIL,
            message=message,
            prompt_message=prompt_message,
        )


async def main():
    atom_service = AtomService()
    link = atom_service.generate_feedback_link("123")
    print("Link:", link)
    conversation_id = str(uuid.uuid4())
    human_msg = await atom_service.create_human_message(conversation_id, "test_email_user", "Hello")
    print("Human message:", human_msg)
    answer = "How are you today?"
    ai_msg = await atom_service.create_ai_message(conversation_id, "test_email_user", answer, {"answer": answer})
    print("AI message:", ai_msg)


if __name__ == "__main__":
    dotenv.load_dotenv(dotenv.find_dotenv())
    asyncio.run(main())
