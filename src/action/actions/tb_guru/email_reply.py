from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ActionResponse
from action.context import ActionContext

entity_prompt = """
## Role

you are a helpful assistant, you need to extract the entities from the user input

## ATTENTION

1. your result should be a json string, like this:

{
    "entity1": "value of entity1",
    "entity2": "value of entity2",
    ...
}
2. DON'T make up entity not listed below.
3. If you cannot find any entity, just return an empty json string like {}.

## User input

{{user_input}}

## Entities info

{{entity_types_and_values}}
"""

new_email_prompt = """
## Email Info

{{email_content}}

## User input

{{user_input}}

## Attention

Write an Email to answer user's question based on above info.
Tell the user we cannot answer his/her question if the email info is empty.
You NEED to use placeholder `Dear ***receiver of email***` as receiver of email, and use placeholder `***sender of email***` as sender of email.
"""

convert_email_prompt = """
## Email Content

{{email_content}}

## Attention

Convert the above email content with valid Email format.
The result should only CONTAIN the content of the email, not the email subject.
You NEED to replace receiver of email with placeholder `Dear ***receiver of email***`, and replace sender of email with placeholder `***sender of email***`.
"""


class EmailReplyAction(Action):
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "email_reply"

    async def run(self, context: ActionContext, result: ActionResponse) -> ActionResponse:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            entity_prompt,
            user_input=context.conversation.current_user_input,
            entity_types_and_values=[
                {
                    "name": "should_draft_email",
                    "description": "if the user ask for help to draft an email",
                    "slotType": "bool",
                }
            ],
        )
        chat_message_preparation.log(logger)
        entities = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=1024, jsonable=True, sub_scenario="extract_entity"
        ).get_json_response()
        logger.info(f"extracted entities: {entities}")
        should_draft_email = entities.get("should_draft_email", False)

        chat_message_preparation = ChatMessagePreparation()

        if should_draft_email:
            chat_message_preparation.add_message(
                "user",
                convert_email_prompt,
                email_content=result.answer.get_content_with_extra_info() if result.answer else "",
            )
        else:
            chat_message_preparation.add_message(
                "user",
                new_email_prompt,
                email_content=result.answer.get_content_with_extra_info() if result.answer else "",
                user_input=context.conversation.current_user_input,
            )

        chat_message_preparation.log(logger)
        email_result = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="write_email"
        ).response
        logger.info(f"email result: {email_result}")

        result.answer.content = email_result
        return result
