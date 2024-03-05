from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import (
    ChatResponseAnswer,
    ResponseMessageType,
    AttachmentResponse,
    Attachment,
    UploadFileContentType,
    GeneralResponse,
)
from action.actions.tb_guru.base import TBGuruAction
from third_system.hsbc_connect_api import HsbcConnectApi

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


class FileValidation(TBGuruAction):
    def __init__(self):
        super().__init__()
        self.hsbc_connect_api = HsbcConnectApi()

    def get_name(self) -> str:
        return "file_validation"

    async def _upload_file(self, res: str) -> str:
        files = [Attachment(name=report_filename, contents=res, content_type=UploadFileContentType.HTML, path="")]
        links = await self.unified_search.upload_files_to_minio(files)
        if links and links[0]:
            return links[0]
        raise Exception("Upload file failed.")

    async def run(self, context):
        logger.info(f"exec action: {self.get_name()} ")

        first_file = await self.download_first_file_contents(context)
        if not first_file:
            return GeneralResponse.normal_failed_text_response(
                "No file uploaded, please upload a file and try again.", context.conversation.current_intent.name
            )

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        res = await self.hsbc_connect_api.validate_file(first_file)
        download_link = await self._upload_file(res)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            prompt,
            user_input=context.conversation.current_user_input,
            file_url=download_link,
            report_filename=report_filename,
            upload_filename=first_file.name,
            upload_file_url=first_file.url,
            upload_file_format=context.conversation.entities[0].value
            if context.conversation.entities
            else first_file.content_type,
        )
        chat_message_preparation.log(logger)

        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=1024)).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )
        attachment = Attachment(path=download_link, name=report_filename, content_type="text/html", url=download_link)
        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachments=[attachment]
        )
