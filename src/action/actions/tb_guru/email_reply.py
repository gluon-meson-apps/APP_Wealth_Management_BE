from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ActionResponse, ChatResponseAnswer, GeneralResponse
from action.context import ActionContext

prompt = """
## Email content
{{email_content}}

## Attention
Answer user's question based on above email contents.
Tell the user we cannot answer the question currently if the email content is empty.
You NEED to use placeholder `Dear ***receiver of email***` as receiver of email, and use placeholder `***sender of email***` as sender of email.
"""


class EmailReplyAction(Action):
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "email_reply"

    async def run(self, context: ActionContext, answer: ChatResponseAnswer) -> ActionResponse:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            """## User question\n{{user_input}}""",
            user_input=context.conversation.current_user_input,
        )
        chat_message_preparation.add_message(
            "system",
            prompt,
            email_content=answer.get_content_with_extra_info() if answer else "",
        )
        chat_message_preparation.log(logger)

        result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=1024).response
        logger.info(f"email result: {result}")

        answer.content = result
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
