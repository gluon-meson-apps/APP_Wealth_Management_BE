import json
from json import JSONDecodeError

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger
from pydantic import BaseModel

from nlu.intent_config import IntentListConfig
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

from prompt_manager.base import PromptWrapper


class IntentClassificationResponse(BaseModel):
    intent: str
    confidence: float


class IntentCall:
    def __init__(
        self,
        intent_list_config: IntentListConfig,
        template: PromptWrapper,
    ):
        self.intent_list_config = intent_list_config
        self.template = template
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "intent_call"

    def construct_system_prompt(
        self, chat_message_preparation: ChatMessagePreparation, full_name_of_parent_intent: str = None
    ):
        intent_list = []
        for intent in self.intent_list_config.intents:
            if intent.full_name_of_parent_intent == full_name_of_parent_intent:
                descriptions = [intent.description]
                children_intents = self.intent_list_config.get_children_intents(intent)
                descriptions.extend([intent.description for intent in children_intents])
                intent_list.append({"name": intent.name, "description": descriptions})

        chat_message_preparation.add_message("system", self.template.template, intent_list=json.dumps(intent_list))

    async def classify_intent(
        self, query: str, examples, session_id, full_name_of_parent_intent: str = None
    ) -> IntentClassificationResponse:
        # TODO: drop history if it is too long
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, session_id)

        chat_message_preparation = ChatMessagePreparation()

        self.construct_system_prompt(chat_message_preparation, full_name_of_parent_intent)
        logger.debug(examples)

        for example in examples:
            chat_message_preparation.add_message("user", example["example"])
            chat_message_preparation.add_message("assistant", example["intent"])

        chat_message_preparation.add_message("user", query)
        chat_message_preparation.log(logger)

        intent = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                max_length=64,
                jsonable=True,
                sub_scenario=full_name_of_parent_intent,
            )
        ).get_json_response()
        logger.debug(intent)
        try:
            response = IntentClassificationResponse.model_validate(intent)
        except JSONDecodeError as e:
            logger.error(e)
            response = IntentClassificationResponse(intent="unknown", confidence=1.0)
        return response
