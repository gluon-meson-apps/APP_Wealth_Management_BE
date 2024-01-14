import json
from json import JSONDecodeError
from typing import List

from loguru import logger
from pydantic import BaseModel

from llm.self_host import ChatModel
from nlu.intent_config import IntentConfig
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

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

    def construct_system_prompt(self, chat_history: list[dict[str, str]]):
        intent_list_str = json.dumps(
            [{"name": intent.name, "description": intent.description} for intent in self.intent_list]
        )

        chat_history_str = ""
        for chat in chat_history:
            i_or_you = "I" if chat["role"] == "user" else "You"
            chat_history_str += f"{i_or_you}: {chat['content']}\n"

        system_message = self.template.format_jinja(intent_list=intent_list_str, chat_history=chat_history_str)
        return system_message

    def format_message(self, role, content):
        return dict(role=role, content=content)

    def classify_intent(
        self, query: str, chat_history: list[dict[str, str]], examples, session_id
    ) -> IntentClassificationResponse:
        system_message = self.construct_system_prompt(chat_history)
        history = [{"role": "system", "content": system_message}]
        logger.debug(examples)
        for example in examples:
            history.append(self.format_message("user", example["example"]))
            history.append(self.format_message("assistant", example["intent"]))
        gm_history = [(h["role"], h["content"]) for h in history]
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, session_id)

        # TODO: drop history if it is too long
        intent = chat_model.chat(query, history=gm_history, max_length=4096).response
        logger.debug(query)
        logger.debug(history)
        logger.debug(system_message)
        logger.debug(intent)
        try:
            response = IntentClassificationResponse.parse_obj(json.loads(intent))
        except JSONDecodeError as e:
            logger.error(e)
            response = IntentClassificationResponse(intent="unknown", confidence=1.0)
        return response
