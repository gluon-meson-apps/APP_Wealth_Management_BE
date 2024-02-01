import asyncio
import mimetypes
import os
from typing import Union

import aiohttp
from loguru import logger

from action.base import UploadFileContentType, UploadStorageFile
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
            self.base_url + "/search", json=search_param.model_dump(), headers={"conversation-id": conversation_id}
        )
        print(response.json())
        return [SearchResponse.model_validate(item) for item in response.json()]

    async def async_search(self, search_param: SearchParam, conversation_id) -> list[SearchResponse]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/search",
                    json=search_param.model_dump(),
                    headers={"conversation-id": conversation_id},
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return [SearchResponse.model_validate(item) for item in result]
            except Exception as err:
                logger.error(f"Error search {search_param}:", err)
                return []

    def vector_search(self, search_param: SearchParam, table) -> list[SearchResponse]:
        response = requests.post(f"{self.base_url}/vector/{table}/search/", json=search_param.dict())
        print(response.json())
        return [handle_response(response)]

    async def async_vector_search(self, search_param: SearchParam, table) -> list[SearchResponse]:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/vector/{table}/search/", json=search_param.dict()) as response:
                return [await handle_aio_response(response)]

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

    async def upload_file_to_minio(self, files: list[UploadStorageFile]) -> list[str]:
        data = aiohttp.FormData()
        for f in files:
            if (f.file_path and os.path.exists(f.file_path)) or f.contents:
                data.add_field(
                    "files",
                    f.contents if f.contents else open(f.file_path, "rb"),
                    filename=f.filename,
                    content_type=f.content_type if f.content_type else mimetypes.guess_type(f.filename)[0],
                )
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/file", data=data) as response:
                return await response.json()


async def main():
    files = [
        UploadStorageFile(
            filename="test.txt",
            file_path="../resources/prompt_templates/slot_confirm.txt",
            content_type=UploadFileContentType.TXT,
        ),
    ]
    result = await UnifiedSearch().upload_file_to_minio(files)
    print(result)

    UnifiedSearch().search(
        SearchParam(
            query="Hi TB Guru, please help me to cross check the standard pricing of ACH payment in Singapore and see if I can offer a unit rate of SGD 0.01 to the client.",
        ),
        conversation_id="test",
    )


if __name__ == "__main__":
    asyncio.run(main())
