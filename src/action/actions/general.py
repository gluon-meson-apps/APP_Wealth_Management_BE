from typing import List
from loguru import logger
from action.base import Action, ActionResponse
from llm.self_host import ChatModel
from nlu.intent_with_entity import Intent, Slot
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext


DEFAULT_END_UTTERANCE = "感谢您的使用，祝您生活愉快"

class EndDialogueAction(Action):
    """action to end the conversation with user"""

    def run(self, context):
        return ActionResponse(text=DEFAULT_END_UTTERANCE)

class SlotFillingAction(Action):
    """Slot filling action using large language models."""

    def __init__(self, slots: List[Slot], intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='slot_filling')
        self.llm = ChatModel()
        self.slots = slots
        self.intent = intent

    def run(self, context):
        logger.info(f'exec action slot filling')
        prompt = self.prompt_template.format({
            "fill_slot": self.slots.pop().description,
            "intent": self.intent.description,
            "history": context.conversation.get_history().format_to_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=1024)
        detail = {
            "slot": [(slot.name, slot.value, slot.confidence) for slot in self.slots],
            "intent": self.intent
        }
        return ActionResponse(text=response, extra_info=detail)

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
        response = self.llm.chat(prompt, max_length=256)
        detail = {
            "intent": self.intent
        }
        return ActionResponse(text=response, extra_info=detail)
    

class IntentFillingAction(Action):
    """Intent filling action using large language models."""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='intent_filling')
        self.llm = ChatModel()

    def run(self, context):
        logger.info(f'exec action intent_filling')
        prompt = self.prompt_template.format({
            "history": context.conversation.get_history().format_to_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=256)
        return ActionResponse(text=response)

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
        response = self.llm.chat(prompt, max_length=256)
        detail = {
            "intent": self.intent
        }
        return ActionResponse(text=response, extra_info=detail)

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