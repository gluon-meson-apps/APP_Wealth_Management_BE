import os
import shutil
import uuid

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
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch
from utils.ppt_helper import plot_graph, ppt_generation

report_filename = "file_validation_report.html"

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

    def _generate_ppt(self, df_current: pd.DataFrame, df_all: pd.DataFrame, insight: str) -> str:
        company_name = df_current.iloc[0]["company"] if "company" in df_current.iloc[0] else ""
        latest_days = df_all.iloc[0]["days"] if "days" in df_all.iloc[0] else ""
        if company_name and latest_days:
            files_dir = f"{self.tmp_file_dir}/{str(uuid.uuid4())}"
            os.makedirs(files_dir, exist_ok=True)
            image_paths = [f"{files_dir}/image1.png", f"{files_dir}/image2.png"]
            ppt_path = f"{files_dir}/ppt.pptx"
            plot_graph(df_current, f"{company_name} – Working Capital Metrics Trend", "days", image_paths[0])
            plot_graph(df_all, f"Peer Comparison ({latest_days})", "company", image_paths[1])
            df_all = df_all.drop(columns=["days"])
            ppt_generation(
                df_all, llm_insight=insight, company_name=company_name, image_paths=image_paths, output_path=ppt_path
            )
            files = [
                ("files", ("tb_guru_ppt.pptx", open(ppt_path, "rb"), UploadFileContentType.PPTX)),
            ]
            links = self.unified_search.upload_file_to_minio(files)
            shutil.rmtree(files_dir)
            return links[0] if links else ""
        return ""

    async def _search(self, entity_dict, session_id) -> tuple[pd.DataFrame, pd.DataFrame]:
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
        latest_all_data = list(filter(lambda s: s.days == latest_period, all_companies_data)) if latest_period else []
        df_current = pd.DataFrame([w.model_dump() for w in current_company_data])
        df_all = pd.DataFrame([w.model_dump() for w in latest_all_data])
        df_current = df_current.drop(columns=["meta__score", "meta__reference", "id"])
        df_all = df_all.drop(columns=["meta__score", "meta__reference", "id"])
        return df_all, df_current

    async def run(self, context) -> ActionResponse:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        logger.info(f"exec action: {self.get_name()} ")

        entity_dict = context.conversation.get_simplified_entities()
        is_ppt_output = entity_dict["is_ppt_output"] if "is_ppt_output" in entity_dict else False

        df_all_companies_data, df_current_company_data = await self._search(
            entity_dict, context.conversation.session_id
        )

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            """## User question\n{{user_input}}""",
            user_input=context.conversation.current_user_input,
        )
        chat_message_preparation.add_message(
            "assistant",
            """## WCS data are extracted already\n{{wcs_data}}""",
            wcs_data=df_all_companies_data.to_json(orient="records")
            + df_current_company_data.to_json(orient="records"),
        )
        chat_message_preparation.log(logger)

        result = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="insight"
        ).response
        logger.info(f"chat result: {result}")

        if is_ppt_output and not df_current_company_data.empty and not df_all_companies_data.empty:
            ppt_link = self._generate_ppt(df_current_company_data, df_all_companies_data, result)

            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message("system", ppt_prompt, ppt_link=ppt_link)
            chat_message_preparation.log(logger)

            result = chat_model.chat(
                **chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="ppt"
            ).response
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
