from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import (
    ChatResponseAnswer,
    ResponseMessageType,
    GeneralResponse,
)
from action.actions.tb_guru.base import TBGuruAction
from third_system.search_entity import SearchParam

prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's query base on provided Board Resolution extension content.

## Board Resolution extension content
{{br_extension_content}}

## User input
{{user_input}}

## INSTRUCTION
Now, answer the user's question, and reply the final result.
"""

summary_prompt = """
## INSTRUCTION
please summarize the user question according USER INPUT and chat history

## user input

{{user_input}}

## chat history

{{chat_history}}

"""


class BRExtensionQAAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "br_extension_qa"

    async def run(self, context):
        logger.info(f"exec action: {self.get_name()} ")

        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        user_input = context.conversation.current_user_input
        history = context.conversation.get_history().format_string()
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message("user", summary_prompt, user_input=user_input, chat_history=history)
        chat_message_preparation.log(logger)

        summary_user_input = (
            await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=512, sub_scenario="summary")
        ).response

        query = f"""## User input:
search the BR requirements
## User question
{summary_user_input}
"""
        logger.info(f"search query: {query}")

        response = await self.unified_search.search(SearchParam(query=query, tags={"product_line": "BR extension"}), context.conversation.session_id)
        logger.info(f"search response: {response}")

        if len(response) == 0 or response[0].is_empty():
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content="Sorry, I can't answer your question, since there is no BR extension documents information found.",
                intent=context.conversation.current_intent.name,
            )
            return GeneralResponse(code=200, message="failed", answer=answer, jump_out_flag=False)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message("system", prompt, user_input=user_input, br_extension_content=response)
        chat_message_preparation.log(logger)

        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(), max_length=2048, sub_scenario="final_question"
            )
        ).response
        logger.info(f"chat result: {result}")
        references = []
        for res in response:
            references += res.items

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
            references=references,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
