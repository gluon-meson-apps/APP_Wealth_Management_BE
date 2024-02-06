from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from action.context import ActionContext
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch
from utils.utils import get_texts_from_search_response_list

prompt = """## Role
You are a helpful assistant, you need to answer the question from user based on below info.

## business resolution file content
{{br_file_content}}

## Training document
{{training_doc}}

## user input
{{user_input}}

## instruction
Now, answer the user's question, and reply the result.
"""

no_data_prompt = """## Role
You are a helpful assistant, you need to answer the question from user based on below info.

## Training document

## user input
{{user_input}}

## instruction
Ask the user to check their input because you cannot find related content in training document.
"""


class BrFileValidation(Action):
    def __init__(self) -> None:
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "br_file_validation"

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input
        contents = context.conversation.uploaded_file_contents

        search_res = await self.unified_search.vector_search(SearchParam(query=user_input, size=2), "training_doc")
        training_doc = get_texts_from_search_response_list(search_res)

        br_file_contents = get_texts_from_search_response_list(contents) if training_doc else ""

        chat_message_preparation = ChatMessagePreparation()
        if training_doc:
            chat_message_preparation.add_message(
                "user",
                prompt,
                br_file_content=br_file_contents,
                user_input=user_input,
                training_doc=training_doc,
            )
        else:
            chat_message_preparation.add_message("system", no_data_prompt, user_input=user_input)
        chat_message_preparation.log(logger)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                max_length=1024,
                sub_scenario="validation" if br_file_contents else "no_data",
            )
        ).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
            references=search_res[0].items if search_res else [],
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
