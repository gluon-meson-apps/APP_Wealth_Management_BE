from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

prompt = """## ROLE
you are a helpful chatbot, extract all the session names from this discussion:

## history
{{history}}
"""


class SummarizeHistory:
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "summarize_history"

    async def summarize(self, history: str, session_id: str):
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
