from typing import Union

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import (
    Action,
    ChatResponseAnswer,
    ResponseMessageType,
    AttachmentResponse,
    Attachment,
    UploadFileContentType,
    UploadStorageFile,
)
from third_system.hsbc_connect_api import HsbcConnectApi
from third_system.search_entity import SearchResponse, SearchItem
from third_system.unified_search import UnifiedSearch

report_filename = "file_validation_report.html"

prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's query.

## Reference info
You DO NOT need the file to process file validation because the file validation is already done by another system.
BUT PRETEND you did the file validation.
The URL to download the validation report is attached below and the validation report is a html file.

## Reply requirements
Your reply should include following 2 parts:
1. Your reply should include the upload file info
2. Your reply should include the report info and tell the user to download the report to check if the file valid or not.
   please note: the report URL link should be wrapped by a HTML <a> tag with target="_blank" attribute. like this <a href="$your_url" target="_blank">$file_name</a>

## User upload file info
Upload file name: {{upload_filename}}
Upload file URL: {{upload_file_url}}
Upload file format: {{upload_file_format}}

## Validation report file info
Report file name: {{report_filename}}
Report file URL: {{file_url}}

## User query
{{user_input}}

## INSTRUCTION
Now, answer the user's question, and reply the final result.
"""


def get_first_file(context) -> Union[SearchItem, None]:
    if context.conversation.uploaded_file_contents:
        file_response: SearchResponse = context.conversation.uploaded_file_contents[0]
        return file_response.items[0] if file_response.items else None
    return None


class FileValidation(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.hsbc_connect_api = HsbcConnectApi()

    def get_name(self) -> str:
        return "file_validation"

    async def _upload_file(self, res: str) -> str:
        files = [UploadStorageFile(filename=report_filename, file_path=res, content_type=UploadFileContentType.HTML)]
        links = await self.unified_search.upload_file_to_minio(files)
        if links and links[0]:
            return links[0]
        raise Exception("Upload file failed.")

    async def run(self, context):
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        logger.info(f"exec action: {self.get_name()} ")

        first_file: SearchItem = get_first_file(context)

        res = self.hsbc_connect_api.validate_file(first_file)
        download_link = await self._upload_file(res)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            prompt,
            user_input=context.conversation.current_user_input,
            file_url=download_link,
            report_filename=report_filename,
            upload_filename=first_file.meta__reference.meta__source_name,
            upload_file_url=first_file.meta__reference.meta__source_url,
            upload_file_format=context.conversation.entities[0].value
            if context.conversation.entities
            else first_file.meta__reference.meta__source_type,
        )
        chat_message_preparation.log(logger)

        result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=1024).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )
        attachment = Attachment(path=download_link, name=report_filename, content_type="text/html", url=download_link)
        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachment=attachment
        )
