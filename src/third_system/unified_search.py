import asyncio
import mimetypes
import os
import re
from typing import Union

import aiohttp
from loguru import logger

from action.base import UploadFileContentType, Attachment
from third_system.search_entity import SearchParam, SearchResponse

unified_search_url = os.environ.get("UNIFIED_SEARCH_URL", "http://localhost:8000")

SPLIT_FILE_TOKEN_SiZE = 2000


async def call_search_api(method: str, endpoint: str, payload: dict) -> SearchResponse:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, json=payload) if method == "POST" else session.get(
                endpoint, params=payload
            ) as response:
                response.raise_for_status()
                return SearchResponse.model_validate(await response.json())
        except Exception as err:
            logger.error(f"Error fetch url {endpoint}: {err}")
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
                logger.error(f"Error search {search_param}: {err}")
                return []

    async def vector_search(self, search_param: SearchParam, table) -> list[SearchResponse]:
        result = await call_search_api("POST", f"{self.base_url}/vector/{table}/search/", search_param.model_dump())
        return [result] if result.items else []

    async def upload_intents_examples(self, table, intent_examples):
        return await call_search_api("POST", f"{self.base_url}/vector/{table}/intent_examples", intent_examples)

    async def search_for_intent_examples(self, table, user_input):
        return await call_search_api("POST", f"{self.base_url}/vector/{table}/search", {"query": user_input})

    async def download_raw_file_from_minio(self, file_url: str) -> Union[Attachment, None]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/file/download_raw", params={"file_url": file_url}) as resp:
                    resp.raise_for_status()
                    file_name = re.findall('filename="(.+)"', resp.headers.get("Content-Disposition", ""))
                    content = await resp.content.read()
                    return Attachment(
                        path="",
                        url=file_url,
                        name=file_name[0] if file_name else "",
                        contents=content,
                        content_type=resp.headers.get("Content-Type", ""),
                    )
            except Exception as err:
                logger.error(f"Error download {file_url}: {err}")
                return None

    async def download_file_from_minio(
        self, file_url: str, chunk_size: int = SPLIT_FILE_TOKEN_SiZE, chunk_overlap: int = 0
    ) -> SearchResponse:
        return await call_search_api(
            "GET",
            f"{self.base_url}/file/download",
            {"file_url": file_url, "chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
        )

    async def upload_file_to_minio(self, files: list[Attachment], file_urls: list[str] = None) -> list[str]:
        data = aiohttp.FormData()
        if file_urls:
            for url in file_urls:
                data.add_field("file_urls", url)
        for f in files:
            if (f.path and os.path.exists(f.path)) or f.contents:
                data.add_field(
                    "files",
                    f.contents if f.contents else open(f.path, "rb"),
                    filename=f.name,
                    content_type=f.content_type if f.content_type else mimetypes.guess_type(f.filename)[0],
                )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/file", data=data) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as err:
            logger.error(f"Error upload files: {err}")
            return []

    async def generate_file_link(self, filename: str) -> str:
        endpoint = f"{self.base_url}/file/link"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, json={"filename": filename}) as response:
                    response.raise_for_status()
                    return await response.json()
            except Exception as err:
                logger.error(f"Error fetch url {endpoint}: {err}")
                return ""


async def main():
    files = [
        Attachment(
            name="test.txt",
            path="../resources/prompt_templates/slot_confirm.txt",
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
