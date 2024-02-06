from typing import Optional

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import (
    DefaultScenarioModelRegistryCenter,
    BaseScenarioModelRegistryCenter,
)
from loguru import logger

from tracker.context import ConversationContext


class IntentChoosingConfirmer:
    def __init__(
        self,
        intent_choosing_template: str,
        model_registry: BaseScenarioModelRegistryCenter = DefaultScenarioModelRegistryCenter(),
    ):
        self.scenario_model_registry = model_registry
        self.scenario_model = "intent_choosing_confirm"
        self.intent_choosing_template = intent_choosing_template

    async def confirm(self, conversation: ConversationContext, session_id: str) -> Optional[str]:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, session_id)

        chat_message_preparation = ChatMessagePreparation()

        chat_message_preparation.add_message(
            "system",
            self.intent_choosing_template,
            history=conversation.get_history().format_string(),
            intent_list=[intent.minimal_info() for intent in conversation.confused_intents],
        )
        chat_message_preparation.log(logger)

        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(), max_length=64, jsonable=True, sub_scenario="intent"
            )
        ).get_json_response()

        if result["user_reply_with_intent"]:
            return result["intent"]
        return None
