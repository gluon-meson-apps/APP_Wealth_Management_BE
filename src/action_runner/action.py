from abc import ABC, abstractmethod
from typing import List

import requests
from gluon_meson_sdk.models.chat_model import ChatModel
from pydantic import BaseModel

from action_runner.context import ActionContext
from nlu.intent_with_entity import Intent, Slot
from prompt_manager.base import BasePromptManager

GLUON_MESON_MASTER_ENDPOINT = "http://10.207.227.101:18000"

from gm_logger import get_logger

logger = get_logger()

class ActionResponse(BaseModel):
    text: str
    extra_info: dict = {}


class Action(ABC):
    """Base abstract class for all actions."""

    @abstractmethod
    def run(self, context: ActionContext) -> ActionResponse:
        """Run the action given the context."""
        pass


class SmartHomeOperatingAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        logger.debug("成功控制了智能家居")
        return ActionResponse(text=self.response)


class ChitChatAction(Action):
    def __init__(self, model_name, chat_model: ChatModel, user_input):
        self.model_name = model_name
        self.chat_model = chat_model
        self.user_input = user_input

    def run(self, context) -> ActionResponse:
        # todo: add history from context
        response = self.chat_model.chat_single(self.user_input, model_type=self.model_name, max_length=1000)
        return ActionResponse(text=response.response)



class ChatAction(Action):
    """Chat action using large language models."""

    def __init__(self, style, model_name):
        """
        Initialize the chat action.
        
        Args:
            style: Prompt style to use.
            model_name: Name of model to use for chat.
        """
        prompt_manager = BasePromptManager()
        self.prompt_template = prompt_manager.load(domain='response', style=style)
        self.model = model_name
        self.llm = ChatModel(master_endpoint=GLUON_MESON_MASTER_ENDPOINT)

    def run(self, context):
        """
        Run the chat action.
        
        Args:
            context: The action context.
            
        Returns:
            The chat response.
        """
        user_input = context.get_user_input()
        prompt = self.prompt_template.format({"input": user_input})
        response = self.llm.chat_single(prompt, model_type=self.model)
        return response.response


class SlotFillingAction(Action):
    """Slot filling action using large language models."""

    def __init__(self, model_name, slots: List[Slot], intent: Intent):
        """
        Initialize the slot filling action.
        
        Args:
            style: Prompt style to use. 
            model_name: Name of model to use for slot filling.
        """
        prompt_manager = BasePromptManager()
        self.prompt_template = prompt_manager.load(domain='slot_filling')
        self.model = model_name
        self.llm = ChatModel(master_endpoint=GLUON_MESON_MASTER_ENDPOINT)
        self.slots = slots
        self.intent = intent

    def run(self, context):
        """
        Run the slot filling action.
        
        Args:
            context: The action context.
            
        Returns:
            The slot filling response.
        """
        slots = self.slots
        # not_filled_slot = [k for k, v in slots.items() if v is None]
        prompt = self.prompt_template.format({
            "fill_slot": self.slots.pop().name,
            "intent": self.intent.name,
            "history": context.conversation.get_history().format_to_string(),
        })
        response = self.llm.chat_single(prompt, model_type=self.model, max_length=4000)
        return ActionResponse(text=response.response)


class FixedAnswerAction(Action):
    """Fixed response action giving pre-defined answers."""

    PresetResponses = {
        "评价": "请对我的服务进行评价,谢谢!",
        "打招呼": "您好,请问有什么可以帮助您的吗?",
        "结束对话": "再见,祝您生活愉快!"
    }

    def __init__(self, response_policy):
        """
        Initialize the fixed response action.
        
        Args:
            response_policy: Key of pre-defined response to use.
        """
        self.response = self.PresetResponses.get(response_policy)

    def run(self, context):
        """
        Run the fixed response action.
        
        Returns:
            Pre-defined response string.
        """
        return self.response


class ApiAction(Action):
    """API call action."""

    def __init__(self, api_url, method='GET', slot_used: dict = None, data=None, headers=None):
        """
        Initialize the API action.
        
        Args:
            api_url: URL of API to call.
            method: HTTP method to use.
            slot_used: Slots to insert into API call.
            data: Request body data. 
            headers: Custom headers to add.
        """
        self.api_url = api_url
        self.method = method
        self.slot_used = slot_used
        self.data = data
        self.headers = headers

    def parse_output(response):
        """Parse the API response."""
        return response

    def run(self, context):
        """
        Run the API action.
        
        Args:
            context: The action context.
            
        Returns:
            The API response.
        """
        params_dict = {}
        for key in self.slot_used:
            params_dict[key] = context.get_slot(key)

        response = requests.request(
            method=self.method,
            url=self.api_url,
            params=params_dict,
            data=self.data,
            headers=self.headers
        )
        return self.parse_output(response.text)
