import os
import shutil
import uuid
from typing import Union, Any

import pandas as pd
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from loguru import logger

from action.base import (
    Action,
    ChatResponseAnswer,
    ResponseMessageType,
    GeneralResponse,
    ActionResponse,
    UploadFileContentType,
)
from third_system.search_entity import SearchItem, SearchParam
from third_system.unified_search import UnifiedSearch
from utils.ppt_helper import plot_graph, ppt_generation

report_filename = "file_validation_report.html"

prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's question.

## User question
{{user_input}}
Please IGNORE my requirements for PPT and DO NOT mention anything about PPT in your reply.
You also DO NOT need to extract data from WSC system because I will provide you WCS data as below.

## WCS data
{{wcs_data}}

## Instruction
The data needed are already extracted from WCS system and attached above. Use this data to answer user's question.
If the WCS data is empty, then tell the user that we cannot find data, ask them to check their input question.
Now, answer user's question and reply the result.
"""

ppt_prompt = """
## Reference info
You are an assistant with name as "TB Guru".
We have generated a PPT for the user and the link is attached below, tell the user to download it.
If the PPT link is empty, tell the user that we cannot generate PPT now. Please ask them to try again later.

## PPT link
{{ppt_link}}

## Instruction
now, reply your result.
"""


class WcsDataQuery(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.tmp_file_dir = os.path.join(os.path.dirname(__file__), "../../../../", "tmp/wcs")

    def get_name(self) -> str:
        return "wcs_data_query"

    def _generate_ppt(
        self, current_company_data: list[SearchItem], all_companies_data: list[SearchItem], insight: str
    ) -> str:
        file_dir = f"{self.tmp_file_dir}/{str(uuid.uuid4())}"
        os.makedirs(file_dir, exist_ok=True)
        image_paths = [f"{file_dir}/image1.png", f"{file_dir}/image2.png"]
        ppt_path = f"{file_dir}/ppt.pptx"
        df_current = pd.DataFrame([w.model_dump() for w in current_company_data])
        df_all = pd.DataFrame([w.model_dump() for w in all_companies_data])
        company_name = current_company_data[0].company
        plot_graph(df_current, f"{company_name} – Working Capital Metrics Trend", "days", image_paths[0])
        plot_graph(df_all, f"Peer Comparison ({all_companies_data[0].days})", "company", image_paths[1])
        df_all = df_all.drop(columns=["days", "meta__score", "meta__reference", "id"])
        ppt_generation(
            df_all, llm_insight=insight, company_name=company_name, image_paths=image_paths, output_path=ppt_path
        )
        files = [
            ("files", ("tb_guru_ppt.pptx", open(ppt_path, "rb"), UploadFileContentType.PPTX)),
        ]
        links = self.unified_search.upload_file_to_minio(files)
        shutil.rmtree(file_dir)
        return links[0] if links else ""

    async def _search(
        self, entity_dict, session_id
    ) -> tuple[Union[list[SearchItem], list[Any]], Union[list[SearchItem], list[Any]]]:
        query_list = [
            f"""Query WCS data with days as {entity_dict["days"]}:"""
            if "days" in entity_dict
            else "Query WCS data sort by days descending:"
        ]
        if "company" in entity_dict:
            query_list.append(f"""Query WCS data with company {entity_dict["company"]}:""")
        search_res = [self.unified_search.search(SearchParam(query=q), session_id) for q in query_list]
        items = [s[0].items if s else [] for s in search_res]
        all_companies_data, current_company_data = items[0], items[1] if len(items) > 1 else []
        latest_period = all_companies_data[0].days if all_companies_data else ""
        return list(
            filter(lambda s: s.days == latest_period, all_companies_data)
        ) if latest_period else [], current_company_data

    async def run(self, context) -> ActionResponse:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        logger.info(f"exec action: {self.get_name()} ")

        entity_dict = context.conversation.get_simplified_entities()
        is_ppt_output = entity_dict["is_ppt_output"] if "is_ppt_output" in entity_dict else False

        all_companies_data, current_company_data = await self._search(entity_dict, context.conversation.session_id)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            prompt,
            user_input=context.conversation.current_user_input,
            wcs_data="\n".join([item.model_dump_json() for item in current_company_data + all_companies_data]),
        )
        chat_message_preparation.log(logger)

        result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=1024).response
        logger.info(f"chat result: {result}")

        if is_ppt_output and current_company_data and all_companies_data:
            ppt_link = self._generate_ppt(current_company_data, all_companies_data, result)

            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message("user", ppt_prompt, ppt_link=ppt_link)
            chat_message_preparation.log(logger)

            result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=1024).response
            logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)


if __name__ == "__main__":
    file_dir = os.path.join(os.path.dirname(__file__), "../../../../", "tmp/wcs")
    with open(f"{file_dir}/test.txt", "w") as f:
        f.write("test")
