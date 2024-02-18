import os
from typing import List

from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from tracker.context import ConversationContext


summarize_history_count = os.getenv("SUMMARIZE_HISTORY_COUNT", 6)

prompt = """## ROLE
you are a helpful chatbot, extract all the session names from this discussion:

## history
{{history}}
"""


class HistorySummarizer:
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "summarize_history"

    async def summarize_history(self, conversation: ConversationContext):
        history = conversation.get_unsummarized_history()
        # TODO: count history or count token
        if len(history) >= summarize_history_count:
            if conversation.summarized_history_context:
                history.insert(0, {"role": "system", "content": conversation.summarized_history_context})
            summarized_history = await self.summarize(history, conversation.session_id)
            conversation.summarized_history_context = summarized_history
            conversation.history.flag_history_summarized(len(history))
        return conversation

    async def summarize(self, history: List[dict], session_id: str):
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message("system", prompt, history=history)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                max_length=1024,
            )
        ).response
        logger.info(f"chat result: {result}")
        return result
