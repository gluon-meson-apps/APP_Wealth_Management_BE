import json
from json import JSONDecodeError
from typing import List

from gluon_meson_sdk.models.abstract_models.abstract_chat_model import AbstractChatModel
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger
from pydantic import BaseModel

from llm.self_host import ChatModel
from nlu.intent_config import IntentConfig
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

from nlu.intent_with_entity import Intent
from prompt_manager.base import PromptWrapper


class IntentClassificationResponse(BaseModel):
    intent: str
    confidence: float


class IntentCall:
    def __init__(
        self,
        intent_list: List[IntentConfig],
        template: PromptWrapper,
        model: ChatModel,
        model_type: str,
    ):
        self.model = model
        self.model_type = model_type
        self.intent_list = intent_list
        self.template = template
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "intent_call"

    def format_history(self, chat_history: list[dict[str, str]]):
        chat_history_str = ""
        for chat in chat_history:
            i_or_you = "I" if chat["role"] == "user" else "You"
            chat_history_str += f"{i_or_you}: {chat['content']}\n"
        return chat_history_str

    def construct_system_prompt(self, chat_message_preparation: ChatMessagePreparation):
        intent_list_str = json.dumps(
            [{"name": intent.name, "description": intent.description} for intent in self.intent_list]
        )

        chat_message_preparation.add_message("system", self.template.template, intent_list=intent_list_str)

    @classmethod
    def is_true(cls, arg):
        ua = str(arg).upper()
        return "TRUE" == ua

    def check_same_topic(self, chat_model: AbstractChatModel, history):
        prompt = """# ROLE

you are a helpful chatbot, your ONLY job is to estimate if the user is changed to a new topic.

# OUTPUT FORMAT
true/false
"""
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message("system", prompt)
        chat_message_preparation.add_message("user", history)
        result = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=2, jsonable=True, sub_scenario="check_same_topic"
        ).response
        start_new_topic = self.is_true(result)
        return not start_new_topic

    def classify_intent(
        self, query: str, chat_history: list[dict[str, str]], examples, session_id, previous_intent: Intent
    ) -> IntentClassificationResponse:
        # TODO: drop history if it is too long
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, session_id)

        chat_message_preparation = ChatMessagePreparation()

        self.construct_system_prompt(chat_message_preparation)
        logger.debug(examples)

        if previous_intent and self.check_same_topic(chat_model, self.format_history(chat_history)):
            return IntentClassificationResponse(intent=previous_intent.name, confidence=1.0)

        for example in examples:
            chat_message_preparation.add_message("user", example["example"])
            chat_message_preparation.add_message("assistant", example["intent"])

        chat_message_preparation.add_message("user", self.format_history(chat_history[-1:]))

        intent = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=64, jsonable=True, sub_scenario="intent"
        ).response
        logger.debug(intent)
        try:
            response = IntentClassificationResponse.parse_obj(json.loads(intent))
        except JSONDecodeError as e:
            logger.error(e)
            response = IntentClassificationResponse(intent="unknown", confidence=1.0)
        return response
