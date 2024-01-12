from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import Action, ChatResponseAnswer, ResponseMessageType, GeneralResponse, ActionResponse
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch
from utils.action_helper import format_entities_for_search

report_filename = "file_validation_report.html"

prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's question.

## Steps
1. extract data from WCS system
2. use below WCS data to answer user's question.
   If the WCS data is empty, then tell the user that we cannot find data, ask them to check their input question.

## WCS data
{wcs_data}

## user question
{user_input}

## INSTRUCT
now, answer the question step by step, and reply the final result.
"""


class WcsDataQuery(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "wcs_data_query"

    async def run(self, context) -> ActionResponse:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model)
        logger.info(f"exec action: {self.get_name()} ")

        entities_without_ppt = format_entities_for_search(context.conversation, ["is_ppt_output"])
        search_res = self.unified_search.search(
            SearchParam(
                query=f"""
        Query WCS data with below fields:
        {entities_without_ppt}
        """
            )
        )

        wcs_data = search_res[0].items if search_res else []
        final_prompt = prompt.format(
            user_input=context.conversation.current_user_input,
            wcs_data="\n".join([item.model_dump_json() for item in wcs_data]),
        )
        logger.info(f"final prompt: {final_prompt}")
        result = chat_model.chat(final_prompt, max_length=1024).response
        logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
