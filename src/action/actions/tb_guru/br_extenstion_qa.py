from typing import Union, re

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import (
    Action,
    ChatResponseAnswer,
    ResponseMessageType,
    GeneralResponse,
)
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch


prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's query base on provided BR extension content.

## BR extension content
{{br_extension_content}}

## User input
{{user_input}}

## INSTRUCTION
Now, answer the user's question, and reply the final result.
"""


class BRExtensionQAAction(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "br_extension_qa"

    async def run(self, context):
        logger.info(f"exec action: {self.get_name()} ")

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        user_input = context.conversation.current_user_input
        query = f"""## User input:
search the BR extension
## User input
{user_input}
## ATTENTION
2. fields to be queried: {context.conversation.get_entities()}"""
        logger.info(f"search query: {query}")

        response = self.unified_search.search(
            SearchParam(query=query), context.conversation.session_id
        )
        logger.info(f"search response: {response}")

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system", prompt, user_input=user_input, br_extension_content=response
        )
        chat_message_preparation.log(logger)

        result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=2048).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT, content=result, intent=context.conversation.current_intent.name
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)