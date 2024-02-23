import asyncio
from abc import ABC
from typing import Union

from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

from action.base import Action, Attachment
from action.context import ActionContext
from third_system.search_entity import SearchResponse
from third_system.unified_search import UnifiedSearch


def decode_bytes(contents: Union[bytes, None]) -> str:
    return contents.decode("utf-8") if contents else ""


class TBGuruAction(Action, ABC):
    def __init__(self) -> None:
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    async def download_first_file(self, context: ActionContext) -> Union[SearchResponse, None]:
        if len(context.conversation.uploaded_file_urls) == 0:
            return None
        contents = await self.unified_search.download_file_from_minio(context.conversation.uploaded_file_urls[0])
        return contents

    async def download_first_raw_file(self, context: ActionContext) -> Union[Attachment, None]:
        if len(context.conversation.uploaded_file_urls) == 0:
            return None
        file = await self.unified_search.download_raw_file_from_minio(context.conversation.uploaded_file_urls[0])
        file.contents = decode_bytes(file.contents) if file.contents else ""
        return file

    async def download_raw_files(self, context: ActionContext) -> list[Attachment]:
        if len(context.conversation.uploaded_file_urls) == 0:
            return []
        tasks = [
            self.unified_search.download_raw_file_from_minio(url) for url in context.conversation.uploaded_file_urls
        ]
        files_res = await asyncio.gather(*tasks)
        return [
            Attachment(name=f.name, path=f.path, content_type=f.content_type, contents=decode_bytes(f.contents))
            for f in files_res
            if f
        ]
