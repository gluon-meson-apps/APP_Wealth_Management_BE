import tiktoken
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ActionResponse, GeneralResponse, ResponseMessageType, ChatResponseAnswer
from action.context import ActionContext
from third_system.unified_search import UnifiedSearch

MAX_BODY_TOKEN_SiZE = 4096

prompt = """## Role
You are a helpful assistant with name as "TB Guru", you need to answer the user's question.

## user input
{{user_input}}
"""

translate_summary_prompt = """## Role
You are a helpful assistant with name as "TB Guru", you need to translate the provided summary according to user requirements.

## user input
{{user_input}}

## provided summary
{{summary}}

## instruction
Now, translate the provided summary and reply the result.
"""


class SummarizeAndTranslate(Action):
    def __init__(self) -> None:
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "summary_and_translation"

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input
        enc = tiktoken.encoding_for_model("gpt-4")
        token_size = len(enc.encode(user_input))

        if token_size > MAX_BODY_TOKEN_SiZE:
            return GeneralResponse(
                code=200,
                message="success",
                answer="Sorry, the maximum limit for the input is 4096 tokens. Please put the parts that need to be translated or summarized in a TXT file and upload it as an attachment.",
                jump_out_flag=False,
            )

        # entity_dict = context.conversation.get_simplified_entities()
        # is_translation_needed = entity_dict.get("is_translation_needed", False)
        # is_summary_needed = entity_dict.get("is_summary_needed", False)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            prompt,
            user_input=user_input,
        )
        chat_message_preparation.log(logger)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                max_length=MAX_BODY_TOKEN_SiZE,
            )
        ).response
        logger.info(f"final result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )

        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
