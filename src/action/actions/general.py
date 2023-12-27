from typing import List, Union
from loguru import logger
from action.base import Action, ActionResponse, GeneralResponse, ChatResponseAnswer, JumpOutResponse, \
    ResponseMessageType
from llm.self_host import ChatModel
from nlu.forms import FormStore
from nlu.intent_with_entity import Intent, Slot
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext


class EndDialogueAction(Action):
    """action to end the conversation with user"""

    def get_name(self) -> str:
        return 'end_dialogue'

    def run(self, context):
        return JumpOutResponse(code=200, message="success", answer={}, jump_out_flag=True)


class SlotFillingAction(Action):
    """Slot filling action using large language models."""

    def get_name(self) -> str:
        return 'slot_filling'

    def __init__(self, slots: Union[List[Slot], Slot], intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='slot_filling')
        self.llm = ChatModel()
        self.intent = intent
        self.slots = slots

    def run(self, context):
        logger.info('exec action slot filling')
        if isinstance(self.slots, list):
            slot_description = '或'.join(slot.description for slot in self.slots)
        else:
            slot_description = self.slots.description

        prompt = self.prompt_template.format({
            "fill_slot": slot_description,
            "intent": self.intent.description,
            "history": context.conversation.get_history().format_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128, model_type='azure-gpt-3.5-2')
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class IntentConfirmAction(Action):
    """Intent confirm action using large language models."""

    def get_name(self) -> str:
        return 'intent_confirm'

    def __init__(self, intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='intent_confirm')
        self.llm = ChatModel()
        self.intent = intent

    def run(self, context: ConversationContext):
        logger.info('exec action intent confirm')
        prompt = self.prompt_template.format({
            "intent": self.intent.description,
            "history": context.conversation.get_history().format_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128, model_type='azure-gpt-3.5-2')
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class IntentFillingAction(Action):
    """Intent filling action using large language models."""

    def get_name(self) -> str:
        return 'intent_filling'

    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        self.prompt_template = prompt_manager.load(name='intent_filling')
        self.llm = ChatModel()
        self.intents = form_store.intent_list_config.get_intent_list()

    def run(self, context):
        logger.info('exec action intent_filling')
        filtered_intents = [intent.description for intent in self.intents if intent.business]
        prompt = self.prompt_template.format({
            "history": context.conversation.get_history().format_string(),
            "intent_list": "和".join(filtered_intents)
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128, model_type='azure-gpt-3.5-2')
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class SlotConfirmAction(Action):
    """Slot confirm action using large language models."""

    def get_name(self) -> str:
        return 'slot_confirm'

    def __init__(self, intent: Intent, slot: Slot, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name='slot_confirm')
        self.llm = ChatModel()
        self.intent = intent
        self.slot = slot

    def run(self, context: ConversationContext):
        logger.info('exec action slot confirm')
        prompt = self.prompt_template.format({
            "intent": self.intent.description,
            "slot": self.slot.description,
            "slot_value": self.slot.value,
            "history": context.conversation.get_history().format_string(),
        })
        logger.debug(prompt)
        response = self.llm.chat(prompt, max_length=128, model_type="azure-gpt-3.5-2")
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class ChitChatAction(Action):
    def get_name(self) -> str:
        return 'chitchat'

    def __init__(self, model_type: str, chat_model: ChatModel):
        self.model_type = model_type
        self.chat_model = chat_model
        self.default_template = "我不知道该怎么回答好了"

    def run(self, context) -> ActionResponse:
        logger.info('exec action slot chitchat')
        # todo: add history from context
        result = self.chat_model.chat(context.conversation.current_user_input, model_type=self.model_type,
                                      max_length=128)
        if result is None:
            return ActionResponse(code=200, message=self.default_template, jump_out_flag=False)
        else:
            return ActionResponse(code=200, message=result, jump_out_flag=False)


class QAAction(Action):
    def get_name(self) -> str:
        return 'qa_TTBBB'

    def __init__(self, model_type: str, chat_model: ChatModel):
        self.model_type = model_type
        self.chat_model = chat_model
        self.default_template = "我不知道该怎么回答好了"

    def run(self, context) -> ActionResponse:
        logger.info('exec action slot chitchat')
        # todo: add history from context
        result = self.chat_model.chat(context.conversation.current_user_input, model_type=self.model_type,
                                      max_length=256)
        if result is None:
            return ActionResponse(code=200, message=self.default_template, jump_out_flag=False)
        else:
            return ActionResponse(code=200, message=result, jump_out_flag=False)
