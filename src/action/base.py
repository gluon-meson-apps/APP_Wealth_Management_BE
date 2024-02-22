import asyncio
from abc import ABC, abstractmethod
from enum import unique, Enum
from typing import Optional, Union, List

from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from pydantic import BaseModel

from action.context import ActionContext, ActionConfigContext
from third_system.search_entity import SearchItem, SearchResponse
from third_system.unified_search import UnifiedSearch


@unique
class ResponseMessageType(str, Enum):
    FORMAT_INTELLIGENT_EXEC = "FORMAT_INTELLIGENT_EXEC"
    FORMAT_TEXT = "FORMAT_TEXT"


@unique
class NormalizeType(str, Enum):
    STRING = "STRING"
    PERCENTAGE = "PERCENTAGE"
    NUMBER = "NUMBER"


@unique
class UploadFileContentType(str, Enum):
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    CSV = "text/csv"
    HTML = "text/html"
    TXT = "text/plain"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class UploadStorageFile(BaseModel):
    filename: str
    file_path: Union[str, None] = None
    contents: Union[bytes, str, None] = None
    content_type: Union[str, None] = None


class ActionResponseAnswerContent(BaseModel):
    businessId: str
    operateType: str
    operateSlots: dict = {}
    businessInfo: dict = {}


class ActionResponseAnswer(BaseModel):
    messageType: str = (ResponseMessageType.FORMAT_INTELLIGENT_EXEC,)
    content: ActionResponseAnswerContent


class ChatResponseAnswer(BaseModel):
    messageType: str = (ResponseMessageType.FORMAT_TEXT,)
    content: str
    intent: Optional[str] = None
    references: Optional[List[SearchItem]] = None
    extra_info: dict[str, str] = {}

    def get_content_with_extra_info(self, from_email: bool = False):
        # output.answer.content += f"\n\nAttachment\n------------------\n{output.attachment.url}"
        extra_info = self.get_email_extra_info() if from_email else self.get_extra_info()
        return self.content + "<br>" + extra_info

    def get_chatbot_details(self, template: str):
        return "".join(
            [
                template.format(key=key.capitalize(), value=value)
                for key, value in self.extra_info.items()
                if key and key != "Attachment" and value
            ]
        )

    def get_extra_info(self):
        template = """<br><h2>{key}</h2><br>{value}<br>"""
        extra_info_str = (
            template.format(key="Attachment", value=self.extra_info["Attachment"])
            if "Attachment" in self.extra_info
            else ""
        )
        chatbot_detail = self.get_chatbot_details(template)
        chatbot_detail_summary = (
            f"<br><br><h2>Detail Info Inside Chatbot</h2><br><details><summary>details</summary>{chatbot_detail}</details>"
            if chatbot_detail
            else ""
        )
        extra_info = (extra_info_str + chatbot_detail_summary).replace("\n", "<br>")
        return extra_info

    def get_email_extra_info(self):
        template = """<strong>{key}</strong><br>{value}<br>"""
        attachment_str = (
            template.format(key="Attachment", value=self.extra_info["Attachment"])
            if "Attachment" in self.extra_info
            else ""
        )
        extra_info_str = f"<br>{attachment_str}" if attachment_str else ""
        chatbot_detail = self.get_chatbot_details(template)
        chatbot_detail_summary = (
            f"<br><strong>Detail Info Inside Chatbot</strong><br>{chatbot_detail}<br>" if chatbot_detail else ""
        )
        extra_info = (extra_info_str + chatbot_detail_summary).replace("\n", "<br>")
        return extra_info


class ActionResponse(BaseModel):
    code: int
    message: str
    answer: Optional[ActionResponseAnswer]
    jump_out_flag: bool


class GeneralResponse(ActionResponse):
    code: int
    message: str
    answer: ChatResponseAnswer
    jump_out_flag: bool

    @staticmethod
    def normal_failed_text_response(content: str, intent: str):
        return GeneralResponse(
            code=400,
            message="failed",
            answer=ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=content,
                intent=intent,
            ),
            jump_out_flag=False,
        )

    @staticmethod
    def normal_success_text_response(content: str, intent: str):
        return GeneralResponse(
            code=200,
            message="success",
            answer=ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=content,
                intent=intent,
            ),
            jump_out_flag=False,
        )


class Attachment(BaseModel):
    path: str
    name: str
    content_type: str
    url: Union[str, None] = None


class AttachmentResponse(ActionResponse):
    code: int
    message: str
    answer: ChatResponseAnswer
    attachment: Attachment
    jump_out_flag: bool = False


class JumpOutResponse(ActionResponse):
    code: int
    message: str
    answer: dict = {}
    jump_out_flag: bool = True


class ErrorResponse(ActionResponse):
    code: int
    message: str
    answer: dict = {}
    jump_out_flag: bool = True


@unique
class ActionName(str, Enum):
    activate_function = "activate_function"
    page_reduce = "page_reduce"
    page_enlarge = "page_enlarge"
    page_resize = "page_resize"
    add_header = "add_header"
    remove_header = "remove_header"


@unique
class SlotType(str, Enum):
    functions = "functions"
    font_change = "font_change"
    font_target = "font_target"
    header_element = "header_element"
    header_position = "header_position"


SlotTypeToOperateTypeDict = {
    "functions": "ACTIVATE_FUNCTION",
    "font_change": "PAGE_RESIZE_INCREMENT",
    "font_target": "PAGE_RESIZE_TARGET",
    "header_element": "ADJUST_HEADER",
    "header_position": "ADJUST_HEADER",
}

ActionTypeToOperateTypeDict = {
    "activate_function": "ACTIVATE_FUNCTION",
    "page_reduce": "PAGE_RESIZE_INCREMENT",
    "page_enlarge": "PAGE_RESIZE_INCREMENT",
    "page_resize": "PAGE_RESIZE_TARGET",
    "add_header": "ADJUST_HEADER",
    "remove_header": "ADJUST_HEADER",
}

ActionToValidSlotTypesDict = {
    "activate_function": ["functions"],
    "page_reduce": ["font_change", "font_target"],
    "page_enlarge": ["font_change", "font_target"],
    "page_resize": ["font_target"],
    "add_header": ["header_element"],
    "remove_header": ["header_element", "header_position"],
}

SlotTypeToNormalizeTypeDict = {
    "functions": NormalizeType.STRING,
    "font_change": NormalizeType.PERCENTAGE,
    "font_target": NormalizeType.PERCENTAGE,
    "header_element": NormalizeType.STRING,
    "header_position": NormalizeType.NUMBER,
}

ActionToSlotCategoryDict = {
    "page_reduce": "DECREASE",
    "page_enlarge": "INCREASE",
    "add_header": "ADD",
    "remove_header": "REMOVE",
}

SlotTypeToSlotValueTypeDict = {
    "header_element": "NAME",
    "header_position": "INDEX",
}

slotsHaveDefaultValue = [SlotType.font_change]
actionsHaveDefaultValue = [ActionName.page_reduce, ActionName.page_enlarge]


class Action(ABC):
    """Base abstract class for all actions."""

    @abstractmethod
    async def run(self, context: ActionContext) -> ActionResponse:
        """Run the action given the context."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass


class DynamicAction(Action, ABC):
    @abstractmethod
    def load_from_config_context(self, config_context: ActionConfigContext):
        pass


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

    async def download_first_raw_file(self, context: ActionContext) -> str:
        if len(context.conversation.uploaded_file_urls) == 0:
            return ""
        contents = await self.unified_search.download_raw_file_from_minio(context.conversation.uploaded_file_urls[0])
        return decode_bytes(contents)

    async def download_raw_files(self, context: ActionContext) -> list[str]:
        if len(context.conversation.uploaded_file_urls) == 0:
            return []
        tasks = [self.unified_search.download_file_from_minio(url) for url in context.conversation.uploaded_file_urls]
        files_res = await asyncio.gather(*tasks)
        return list(map(decode_bytes, files_res))
