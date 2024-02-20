import json
from typing import Sequence

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger
from action.base import (
    Action,
    ActionResponse,
    GeneralResponse,
    ChatResponseAnswer,
    JumpOutResponse,
    ResponseMessageType,
)
from action.context import ActionContext
from llm.self_host import ChatModel
from nlu.forms import FormStore
from nlu.intent_with_entity import Intent, Slot
from prompt_manager.base import PromptManager
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter


class EndDialogueAction(Action):
    """action to end the conversation with user"""

    def get_name(self) -> str:
        return "end_dialogue"

    async def run(self, context):
        return JumpOutResponse(code=200, message="success", answer={}, jump_out_flag=True)


class SlotFillingAction(Action):
    """Slot filling action using large language models."""

    def get_name(self) -> str:
        return "slot_filling"

    def __init__(self, slots: Sequence[Sequence[Slot]], intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name="slot_filling")
        self.intent = intent
        self.slots = slots[0]
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "slot_filling_action"

    def get_slot_names(self):
        result = []
        for slots in self.slots:
            result.append([s.name for s in slots])
        return result

    async def run(self, context):
        logger.info("exec action slot filling")
        slots = [slot.minimal_info() for slot in self.slots]

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            self.prompt_template.template,
            fill_slots=json.dumps(slots),
            intent_name=self.intent.name,
            intent_description=self.intent.description,
            history=context.conversation.get_history().format_string(),
        )
        chat_message_preparation.log(logger)

        response = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=256)).response
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class IntentConfirmAction(Action):
    """Intent confirm action using large language models."""

    def get_name(self) -> str:
        return "intent_confirm"

    def __init__(self, intent: Intent, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name="intent_confirm")
        self.llm = ChatModel()
        self.intent = intent
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "intent_confirmation_action"

    async def run(self, context):
        logger.info("exec action intent confirm")

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            self.prompt_template.template,
            intent=self.intent.description,
            history=context.conversation.get_history().format_string(),
        )
        chat_message_preparation.log(logger)

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        response = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=128)).response
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class IntentFillingAction(Action):
    """Intent filling action using large language models."""

    def get_name(self) -> str:
        return "intent_filling"

    def __init__(self, prompt_manager: PromptManager, form_store: FormStore):
        self.prompt_template = prompt_manager.load(name="intent_filling")
        self.llm = ChatModel()
        self.intents = form_store.intent_list_config.get_intent_list()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "intent_filling_action"

    async def run(self, context):
        logger.info("exec action intent_filling")
        filtered_intents = [intent.minial_info() for intent in self.intents if intent.business and not intent.disabled]
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            self.prompt_template.template,
            history=context.conversation.get_history().format_string(),
            intent_list=json.dumps(filtered_intents),
        )
        chat_message_preparation.log(logger)

        response = (
            await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=1024, temperature=0.7)
        ).response
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class AskForIntentChoosingAction(Action):
    """Intent filling action using large language models."""

    def get_name(self) -> str:
        return "intent_choosing"

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name="intent_choosing")
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "intent_choosing_action"

    async def run(self, context: ActionContext):
        logger.info(f"exec action {self.get_name()}")

        filtered_intents = [
            intent.minimal_info() for intent in context.conversation.confused_intents if not intent.disabled
        ]

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            self.prompt_template.template,
            history=context.conversation.get_history().format_string(),
            intent_list=json.dumps(filtered_intents),
        )
        chat_message_preparation.log(logger)

        response = (
            await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=128, temperature=0.2)
        ).response
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class SlotConfirmAction(Action):
    """Slot confirm action using large language models."""

    def get_name(self) -> str:
        return "slot_confirm"

    def __init__(self, intent: Intent, slot: Slot, prompt_manager: PromptManager):
        self.prompt_template = prompt_manager.load(name="slot_confirm")
        self.llm = ChatModel()
        self.intent = intent
        self.slot = slot
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "slot_confirm_action"

    async def run(self, context):
        logger.info("exec action slot confirm")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            self.prompt_template.template,
            intent=self.intent.description,
            slot=self.slot.description,
            slot_value=self.slot.value,
            history=context.conversation.get_history().format_string(),
        )
        chat_message_preparation.log(logger)

        response = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=512)).response
        detail = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=response)
        return GeneralResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class ChitChatAction(Action):
    def get_name(self) -> str:
        return "chitchat"

    def __init__(self, model_type: str, chat_model: ChatModel):
        self.model_type = model_type
        self.chat_model = chat_model
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "chit_chat_action"

    async def run(self, context) -> ActionResponse:
        logger.info("exec action slot chitchat")
        # todo: add history from context
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            context.conversation.current_user_input,
        )
        chat_message_preparation.log(logger)

        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=1024)).response

        answer = ChatResponseAnswer(messageType=ResponseMessageType.FORMAT_TEXT, content=result)
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)


def find_entity(entities, entity_type):
    for entity in entities:
        if entity.type == entity_type:
            return entity
    return None
