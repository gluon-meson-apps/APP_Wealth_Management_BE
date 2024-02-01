import asyncio
import os
from typing import Union

import aiohttp
from loguru import logger

from action.base import UploadFileContentType
from third_system.search_entity import SearchParam, SearchResponse
import requests


def handle_response(response) -> SearchResponse:
    if response.status_code != 200:
        logger.error(f"{response.status_code}: {response.text}")
        return []
    print(response.json())
    return SearchResponse.model_validate(response.json())


async def handle_aio_response(response) -> SearchResponse:
    if response.status != 200:
        logger.error(f"{response.status}: {await response.text}")
        return []
    print(await response.json())
    return SearchResponse.model_validate(await response.json())


def error_handler(exception):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                print(f"An error occurred: {e}")
                raise exception

        return wrapper

    return decorator


unified_search_url = os.environ.get("UNIFIED_SEARCH_URL", "http://localhost:8000")


class UnifiedSearch:
    def __init__(self):
        self.base_url = unified_search_url

    def search(self, search_param: SearchParam, conversation_id) -> list[SearchResponse]:
        response = requests.post(
            self.base_url + "/search", json=search_param.dict(), headers={"conversation-id": conversation_id}
        )
        print(response.json())
        return [SearchResponse.parse_obj(item) for item in response.json()]

    def vector_search(self, search_param: SearchParam, table) -> list[SearchResponse]:
        response = requests.post(f"{self.base_url}/vector/{table}/search/", json=search_param.dict())
        print(response.json())
        return [handle_response(response)]

    async def upload_intents_examples(self, table, intent_examples):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/vector/{table}/intent_examples?recreate=True", json=intent_examples
            ) as response:
                return await handle_aio_response(response)

    async def search_for_intent_examples(self, table, user_input):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/vector/{table}/search", json={"query": user_input}) as response:
                return await handle_aio_response(response)

    async def download_raw_file_from_minio(self, file_url: str) -> Union[bytes, None]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/file/download_raw", params={"file_url": file_url}) as resp:
                    resp.raise_for_status()
                    return await resp.content.read()
            except Exception as err:
                logger.error(f"Error download {file_url}:", err)
                return None

    async def download_file_from_minio(self, file_url: str) -> SearchResponse:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/file/download", params={"file_url": file_url}) as resp:
                return await handle_aio_response(resp)

    async def upload_file_to_minio(self, files) -> list[str]:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/file", files=files) as response:
                return await response.json()


if __name__ == "__main__":

    async def testing():
        files = [
            (
                "files",
                ("test.txt", open("../resources/prompt_templates/slot_confirm.txt", "rb"), UploadFileContentType.TXT),
            ),
        ]
        result = await UnifiedSearch().upload_file_to_minio(files)
        print(result)

        UnifiedSearch().search(
            SearchParam(
                query="Hi TB Guru, please help me to cross check the standard pricing of ACH payment in Singapore and see if I can offer a unit rate of SGD 0.01 to the client."
            )
        )

    asyncio.run(testing())
