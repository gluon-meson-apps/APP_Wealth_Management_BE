from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from action.context import ActionContext
from third_system.search_entity import SearchParam
from utils.utils import get_texts_from_search_response

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


class BrFileValidation(TBGuruAction):
    def __init__(self) -> None:
        super().__init__()

    def get_name(self) -> str:
        return "br_file_validation"

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        first_file = await self.download_first_file(context)
        if not first_file:
            return GeneralResponse.normal_failed_text_response(
                "No file uploaded, please upload a file and try again.", context.conversation.current_intent.name
            )

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input

        search_res = await self.unified_search.vector_search(SearchParam(query=user_input, size=2), "training_doc")
        training_doc = get_texts_from_search_response(search_res[0]) if search_res else ""

        br_file_contents = get_texts_from_search_response(first_file) if training_doc else ""

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
