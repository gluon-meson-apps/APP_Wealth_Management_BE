import re
from loguru import logger

from action.base import Action, ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from action.context import ActionContext
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from third_system.unified_search import UnifiedSearch

prompt = """## Role
You are a helpful assistant, you need to answer the question from user based on the business resolution file.

## business resolution file content

{br_file_content}

## user input

{user_input}

"""


class BrFileQAAction(Action):
    def __init__(self) -> None:
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "br_file_qa"

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        file_content = "\n".join([i.text for i in context.conversation.uploaded_file_contents[0].items])
        br_file_content = re.sub(r"\n+", "\n", file_content)

        chat_model = self.scenario_model_registry.get_model(self.scenario_model)

        # get the url from entity

        final_prompt = prompt.format(
            br_file_content=br_file_content, user_input=context.conversation.current_user_input
        )
        logger.info(f"final prompt: {final_prompt}")
        result = chat_model.chat(final_prompt, max_length=2048).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT, content=result, intent=context.conversation.current_intent.name
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
