from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import ActionResponse
from output_adapter.base import OutputAdapter
from tracker.context import ConversationContext

prompt = """## Role
you are a helpful assistant, your job is to rewrite the Email Content to act like the email is written by the `#sender`(placeholder) and sent to the `#receiver`(placeholder).

## Email Content
{{email_content}}

## ATTENTION
1. Tell the user we cannot answer the question currently if the email content is empty.
2. DON'T mention TB Guru in the email content.
3. The fewer rewrite, the better
4. if email content contains sender and receiver, you HAVE TO replace them with the corresponding placeholder."""

draft_email_request_prompt = """## Role & Task

you are a helpful chatbot, your job is to identify if the user is asking for a draft email.

## History

{{history}}


## OUTPUT

{
    "ask_to_draft_email": true/false
}
"""

draft_email_response_template = "I've drafted an email for you. Please review and send it to the client.\n"

email_reply_template = """Hi User,
{draft_email_response}{email_content}

Best Regards,
TB Guru"""


class EmailOutputAdapter(OutputAdapter):
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_output_adapter"

    def get_name(self) -> str:
        return "email_reply"

    def process_output(self, result: object, conversation: ConversationContext) -> object:
        if not conversation.check_is_email_request() or not isinstance(result, ActionResponse):
            return result
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, conversation.session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            draft_email_request_prompt,
            history=conversation.get_history().format_string(),
        )
        chat_message_preparation.log(logger)
        json_response = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=64, jsonable=True, sub_scenario="draft_email_check"
        ).get_json_response()
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "system",
            prompt,
            email_content=result.answer.content if result.answer else "",
        )
        chat_message_preparation.log(logger)

        email_result = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=4096, sub_scenario="rewrite_email_content"
        ).response
        draft_email_response = draft_email_response_template

        if "ask_to_draft_email" in json_response and json_response["ask_to_draft_email"]:
            email_result = email_result.replace("#receiver", "***receiver of email***").replace(
                "#sender", "***sender of email***"
            )
            email_result = email_reply_template.format(
                draft_email_response=draft_email_response, email_content=email_result
            )
        else:
            email_result = email_result.replace("#receiver", "User").replace("#sender", "TB Guru")

        logger.info(f"email result: {email_result}")

        result.answer.content = email_result + result.answer.get_extra_info()
        return result
