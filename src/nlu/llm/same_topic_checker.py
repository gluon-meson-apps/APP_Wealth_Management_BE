from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger


class SameTopicChecker:
    def __init__(self):
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = "same_topic_check"

    def format_history(
        self,
        chat_history: list[dict[str, str]],
    ):
        chat_history_str = ""
        for chat in chat_history:
            i_or_you = "I" if chat["role"] == "user" else "You"
            chat_history_str += f"{i_or_you}: {chat['content']}\n"
        return chat_history_str

    async def check_same_topic(self, history, session_id):
        prompt = """## ROLE
you are a helpful chatbot

## Tasks
1. estimate if the user is changed to a new topic.
2. if the user is changed to a new topic, reorganize use's new request combine with the history ON BEHALF OF USER.

## ATTENTION
1. the summary should contains details, someone who don't know the history should be able to understand new request.
2. DON'T MENTION the previous request in the summary.
3. DON'T add or miss any information in the summary.


## OUTPUT FORMAT
{"start_new_topic": true/false, "new_request": "describe the new request ON BEHALF OF USER"}
"""
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, session_id)
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message("system", prompt)
        chat_message_preparation.add_message("user", self.format_history(history))
        chat_message_preparation.log(logger)
        result = (
            await chat_model.achat(
                **chat_message_preparation.to_chat_params(),
                max_length=256,
                jsonable=True,
            )
        ).get_json_response()
        logger.info(f"same topic check result: {result}")
        if result:
            return result.get("start_new_topic", False), result.get("new_request", "")
        return False, ""
