from loguru import logger

from action.base import Action, ChatResponseAnswer, ResponseMessageType, GeneralResponse, ErrorResponse
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from third_system.hsbc_connect_api import HsbcConnectApi
from third_system.search_entity import SearchResponse, SearchItem
from third_system.unified_search import UnifiedSearch

report_filename = "file_validation_report.html"

prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's query.

## Reference info
Do NOT actually try to do file validation because the file validation is already done by another system.
BUT PRETEND that you did the file validation.
The URL to download the validation report is attached below and the validation report is a html file.
Tell the user to download the report to check the validation details.

## Validation report file info
File name: {report_filename}
File url: {file_url}

## User query
{user_input}

## INSTRUCTION
Now, answer the user's question, and reply the final result.
"""


def get_first_file_content(context) -> str:
    if context.conversation.uploaded_file_contents:
        file_response: SearchResponse = context.conversation.uploaded_file_contents[0]
        first_file_item: SearchItem = file_response.items[0] if file_response.items else None
        return first_file_item.text if first_file_item else ""
    return ""


class FileValidation(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.hsbc_connect_api = HsbcConnectApi()

    def get_name(self) -> str:
        return "file_validation"

    def _upload_file(self, res: str) -> str:
        file = (report_filename, res, "text/html")
        files = [("files", file)]
        links = self.unified_search.upload_file_to_minio(files)
        if links and links[0]:
            return links[0]
        raise Exception("Upload file failed.")

    def run(self, context):
        chat_model = self.scenario_model_registry.get_model(self.scenario_model)
        logger.info(f"exec action: {self.get_name()} ")

        file_content_text: str = get_first_file_content(context)

        try:
            res = self.hsbc_connect_api.validate_file(file_content_text)
            download_link = self._upload_file(res)

            final_prompt = prompt.format(
                user_input=context.conversation.current_user_input,
                file_url=download_link,
                report_filename=report_filename,
            )
            logger.info(f"final prompt: {final_prompt}")
            result = chat_model.chat(final_prompt, max_length=1024).response
            logger.info(f"chat result: {result}")

            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=result,
                intent=context.conversation.current_intent.name,
            )
            return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
        except FileNotFoundError as e:
            return ErrorResponse(code=404, message=str(e))
        except Exception as e:
            return ErrorResponse(code=500, message=str(e))
