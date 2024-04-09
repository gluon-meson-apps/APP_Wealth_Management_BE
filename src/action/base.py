from abc import ABC, abstractmethod
from enum import unique, Enum
from typing import Optional, Union, List

from loguru import logger
from pydantic import BaseModel

from action.context import ActionContext, ActionConfigContext
from third_system.search_entity import SearchItem


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
    extra_info: dict[str, Union[list[str], str]] = {}

    def get_content_with_extra_info(self, from_email: bool = False):
        extra_info = self.get_email_extra_info() if from_email else self.get_extra_info()
        return self.content + "\n\n<br>" + extra_info if extra_info else self.content

    def get_chatbot_details(self, template: str):
        details = "".join(
            [
                template.format(key=key.capitalize(), value=value)
                for key, value in self.extra_info.items()
                if key and key != "Attachments" and value
            ]
        )
        return details

    def format_attachments_output(self, template) -> str:
        if "Attachments" in self.extra_info:
            attachment_list = "<br>".join(self.extra_info["Attachments"])
            return template.format(key="Attachments", value=attachment_list)
        return ""

    def get_extra_info(self):
        template = """<br><h4>{key}</h4>{value}<br>"""
        chatbot_detail = self.get_chatbot_details(template)
        extra_info = chatbot_detail.replace("\n", "<br>")
        return extra_info

    def get_email_extra_info(self):
        template = """<strong>{key}</strong><br>{value}<br>"""
        attachment_str = self.format_attachments_output(template)
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
    def normal_failed_text_response(content: str, intent: str, references: List[SearchItem] = None):
        return GeneralResponse(
            code=400,
            message="failed",
            answer=ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=content,
                intent=intent,
                references=references
            ),
            jump_out_flag=False,
        )

    @staticmethod
    def normal_success_text_response(content: str, intent: str, references: List[SearchItem] = None):
        return GeneralResponse(
            code=200,
            message="success",
            answer=ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=content,
                intent=intent,
                references=references
            ),
            jump_out_flag=False,
        )


class Attachment(BaseModel):
    path: str
    name: str
    content_type: str
    contents: Union[bytes, str, None] = None
    url: Union[str, None] = None


class AttachmentResponse(ActionResponse):
    code: int
    message: str
    answer: ChatResponseAnswer
    attachments: list[Attachment]
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
