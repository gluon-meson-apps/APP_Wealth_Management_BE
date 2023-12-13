import os
from typing import List, Union
from loguru import logger
from action.base import Action, ActionResponse
from llm.self_host import ChatModel
from nlu.intent_with_entity import Intent, Slot
from prompt_manager.base import PromptManager
from nlu.mlm.intent import IntentListConfig
from tracker.context import ConversationContext
from pydantic import BaseModel


DEFAULT_END_UTTERANCE = "感谢您的使用，祝您生活愉快"

class MiddleActionResponse(BaseModel):
    code: int
    message: str
    answer: dict = {}
    jump_out_flag: bool


class EndDialogueAction(Action):
    """action to end the conversation with user"""

    def run(self, context):
        return ActionResponse(text=DEFAULT_END_UTTERANCE)

class SlotFillingAction(Action):
    """Slot filling action using large language models."""

    def __init__(self, slots: Union[List[Slot], Slot], intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='slot_filling')
        self.llm = ChatModel()
        self.intent = intent
        self.slots = slots

    def run(self, context):
        logger.info(f'exec action slot filling')
        if isinstance(self.slots, list):
            slot_description = '或'.join(slot.description for slot in self.slots)
        else:
            slot_description = self.slots.description
        
        prompt = self.prompt_template.format({
            "fill_slot": slot_description,
            "intent": self.intent.description,
            "history": context.conversation.get_history().format_to_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128)
        detail = {
            "messageType": "FORMAT_TEXT",
            "content": response
        }
        return MiddleActionResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class IntentConfirmAction(Action):
    """Intent confirm action using large language models."""

    def __init__(self, intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='intent_confirm')
        self.llm = ChatModel()
        self.intent = intent

    def run(self, context: ConversationContext):        
        logger.info(f'exec action intent confirm')
        prompt = self.prompt_template.format({
            "intent": self.intent.description,
            "history": context.conversation.get_history().format_to_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128)
        detail = {
            "messageType": "FORMAT_TEXT",
            "content": response
        }
        return MiddleActionResponse(code=200, message="success", answer=detail, jump_out_flag=False)

class IntentFillingAction(Action):
    """Intent filling action using large language models."""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='intent_filling')
        self.llm = ChatModel()
        pwd = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(pwd, '../../', 'resources', 'scenes')
        intent_list_config = IntentListConfig.from_scenes(file_path)
        self.intents = intent_list_config.get_intent_list()

    def run(self, context):
        logger.info(f'exec action intent_filling')
        filtered_intents = [intent.description for intent in self.intents if intent.business]
        prompt = self.prompt_template.format({
            "history": context.conversation.get_history().format_to_string(),
            "intent_list": "和".join(filtered_intents)
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128)
        detail = {
            "messageType": "FORMAT_TEXT",
            "content": response
        }
        return MiddleActionResponse(code=200, message="success", answer=detail, jump_out_flag=False)

class SlotConfirmAction(Action):
    """Slot confirm action using large language models."""

    def __init__(self, intent: Intent, slot: Slot, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='slot_confirm')
        self.llm = ChatModel()
        self.intent = intent
        self.slot = slot

    def run(self, context: ConversationContext):        
        logger.info(f'exec action slot confirm')
        prompt = self.prompt_template.format({
            "intent": self.intent.description,
            "slot": self.slot.description,
            "slot_value": self.slot.value,
            "history": context.conversation.get_history().format_to_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128)
        detail = {
            "messageType": "FORMAT_TEXT",
            "content": response
        }
        return MiddleActionResponse(code=200, message="success", answer=detail, jump_out_flag=False)

class ChitChatAction(Action):
    def __init__(self, model_type: str, chat_model: ChatModel, user_input):
        self.model_type = model_type
        self.chat_model = chat_model
        self.user_input = user_input
        self.default_template = "我不知道该怎么回答好了"

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action slot chitchat')
        # todo: add history from context
        result = self.chat_model.chat_single(self.user_input, model_type=self.model_type, max_length=1000)
        if result.response is None:
            return ActionResponse(text=self.default_template)
        else:
            return ActionResponse(text=result.response)