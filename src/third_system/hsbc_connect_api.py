import os

import aiohttp
import requests
from loguru import logger

from action.base import Attachment


def mock_validate_res():
    file_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    with open(f"{file_dir}/file_validation_report.html", "r") as f:
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = f.read().encode("utf-8")
        return mock_response


class HsbcConnectApi:
    def __init__(self):
        self.base_url = os.getenv("HSBC_CONNECT_API_ENDPOINT")

    async def _call_hsbc_connect_api(self, file: Attachment) -> str:
        data = aiohttp.FormData()
        data.add_field(
            "Attachment",
            file.contents,
            filename=file.name,
            content_type=file.content_type,
        )
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.base_url, data=data, ssl=False) as response:
                    response.raise_for_status()
                    return await response.text()
            except Exception as err:
                logger.error(f"Error to validate file by HSBC api: {err}")
                raise err

    async def validate_file(self, file: Attachment) -> str:
        if file and file.contents:
            return await self._call_hsbc_connect_api(file) if self.base_url else mock_validate_res().text
        raise FileNotFoundError("No file valid.")
