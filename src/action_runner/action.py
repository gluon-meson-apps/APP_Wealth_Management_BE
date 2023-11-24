from abc import ABC, abstractmethod
from typing import List

import requests
from pydantic import BaseModel

from action_runner.context import ActionContext
from nlu.intent_with_entity import Intent, Slot
from prompt_manager.base import PromptManager
from llm.self_host import ChatModel

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
        context.set_status('action:smart_home_operating')
        logger.debug("成功控制了智能家居")
        return ActionResponse(text=self.response)
    

class PrintStatementAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:print_statement')
        logger.debug("成功查询打印了回单")
        return ActionResponse(text=self.response)
    
class FontPageAdjustmentAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:font_page_adjustment')
        logger.debug("成功调整了页面字体")
        return ActionResponse(text=self.response)
    
class AdjustTableColumnAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:adjust_table_column')
        logger.debug("成功调整了表头")
        return ActionResponse(text=self.response)
    
class ActivateFunctionAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:activate_function')
        logger.debug("成功开通了功能")
        return ActionResponse(text=self.response)
    
class QAAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:qa')
        logger.debug("成功跳转到小招X")
        return ActionResponse(text=self.response)


class ChitChatAction(Action):
    def __init__(self, model_type: str, chat_model: ChatModel, user_input):
        self.model_type = model_type
        self.chat_model = chat_model
        self.user_input = user_input
        self.default_template = "我不知道该怎么回答好了"

    def run(self, context) -> ActionResponse:
        context.set_status('action:chitchat')
        # todo: add history from context
        result = self.chat_model.chat(self.user_input, max_length=1000)
        if result is None:
            return ActionResponse(text=self.default_template)
        else:
            return ActionResponse(text=result)


class GreetAction(Action):
    """Chat action using large language models."""

    def __init__(self, prompt_name: str, model_type: str, prompt_manager: PromptManager, prompt_domain: str = None):
        self.greet_prompt_template = prompt_manager.load(domain=prompt_domain, name=prompt_name)
        self.model = model_type
        self.llm = ChatModel()

    def run(self, context):
        context.set_status('action:greet')
        if self.greet_prompt_template is None:
            return None
        prompt = self.greet_prompt_template.format({})
        response = self.llm.chat(prompt)
        return response

class ChatAction(Action):
    """Chat action using large language models."""

    def __init__(self, prompt_domain: str, prompt_name: str, model_type: str, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(domain=prompt_domain, name=prompt_name)
        self.model = model_type
        self.llm = ChatModel()

    def run(self, context):
        context.set_status('action:chat')
        user_input = context.get_user_input()
        prompt = self.prompt_template.format({"input": user_input})
        response = self.llm.chat(prompt)
        return response


class SlotFillingAction(Action):
    """Slot filling action using large language models."""

    def __init__(self, slots: List[Slot], intent: Intent, prompt_manager: PromptManager):
        """
        Initialize the slot filling action.
        
        Args:
            style: Prompt style to use. 
            model_name: Name of model to use for slot filling.
        """
        self.prompt_template = prompt_manager.load(name='action_slot_filling')
        self.llm = ChatModel()
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
        context.set_status('action:slot_filling')
        slots = self.slots
        # not_filled_slot = [k for k, v in slots.items() if v is None]
        prompt = self.prompt_template.format({
            "fill_slot": self.slots.pop().name,
            "intent": self.intent.name,
            "history": context.conversation.get_history().format_to_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=4000)
        return ActionResponse(text=response)


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
        context.set_status('action:fixed_response')
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
        context.set_status('action:api_call')
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
