import asyncio
import base64
import mimetypes
import os
from typing import Union

import aiohttp
from loguru import logger

from action.base import UploadFileContentType, UploadStorageFile
from third_system.search_entity import SearchParam, SearchResponse

unified_search_url = os.environ.get("UNIFIED_SEARCH_URL", "http://localhost:8000")


async def call_search_api(method: str, endpoint: str, payload: dict) -> SearchResponse:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, json=payload) if method == "POST" else session.get(
                endpoint, params=payload
            ) as response:
                response.raise_for_status()
                return SearchResponse.model_validate(await response.json())
        except Exception as err:
            logger.error(f"Error fetch url {endpoint}:", err)
            return SearchResponse()


class UnifiedSearch:
    def __init__(self):
        self.base_url = unified_search_url

    async def search(self, search_param: SearchParam, conversation_id) -> list[SearchResponse]:
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

    async def vector_search(self, search_param: SearchParam, table) -> list[SearchResponse]:
        result = await call_search_api("POST", f"{self.base_url}/vector/{table}/search/", search_param.model_dump())
        return [result] if result.items else []

    async def upload_intents_examples(self, table, intent_examples):
        return await call_search_api("POST", f"{self.base_url}/vector/{table}/intent_examples", intent_examples)

    async def search_for_intent_examples(self, table, user_input):
        return await call_search_api("POST", f"{self.base_url}/vector/{table}/search", {"query": user_input})

    async def download_raw_file_from_minio(self, file_url: str) -> Union[bytes, None]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/file/download_raw", params={"file_url": file_url}) as resp:
                    resp.raise_for_status()
                    return base64.b64decode(await resp.text())
            except Exception as err:
                logger.error(f"Error download {file_url}:", err)
                return None

    async def download_file_from_minio(self, file_url: str) -> SearchResponse:
        return await call_search_api("GET", f"{self.base_url}/file/download", {"file_url": file_url})

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

    search_result = await UnifiedSearch().search(
        SearchParam(
            query="Hi TB Guru, Please help me to extract Apple company data from the @WCS system, and share some data insight with me.",
        ),
        conversation_id="test",
    )
    print(search_result)


if __name__ == "__main__":
    asyncio.run(main())
