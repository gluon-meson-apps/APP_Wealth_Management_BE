from abc import ABC, abstractmethod
from enum import unique, Enum
from typing import Optional, Union, List

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
    jump_out_flag: bool


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
