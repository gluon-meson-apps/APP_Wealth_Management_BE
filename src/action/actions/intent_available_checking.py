from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import (
    Action,
    ActionResponse,
    GeneralResponse,
    ChatResponseAnswer,
    ResponseMessageType,
)
from action.context import ActionContext

prompt = """## Role
you are a chatbot, you need tell user the current feature is suspended

## disabled feature

{{disabled_feature}}

## user input

{{user_input}}

## INSTRUCT

based on the disabled feature and user input, concisely tell user the specific feature is suspended.

"""


class IntentAvailableCheckingAction(Action):
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "intent_available_checking"

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        current_intent = context.conversation.current_intent

        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            prompt,
            disabled_feature=current_intent.description,
            user_input=context.conversation.current_user_input,
        )
        chat_message_preparation.log(logger)

        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=2048)).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT, content=result, intent=current_intent.name
        )

        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
