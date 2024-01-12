import os
import shutil
import uuid

import pandas as pd
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
from utils.action_helper import format_entities_for_search
from utils.ppt_helper import plot_graph, ppt_generation

report_filename = "file_validation_report.html"

prompt = """
## Role
You are an assistant with name as "TB Guru", you need to answer the user's question.

## Reference info
The data needed are already extracted from WCS system and attached below. Please use this data to answer user's question.
If the WCS data is empty, then tell the user that we cannot find data, ask them to check their input question.
Please note: IGNORE user's requirements for generating PPT and do NOT mention any PPT things in your reply.

## WCS data
{wcs_data}

## user question
{user_input}

## INSTRUCT
now, answer the question step by step, and reply the final result.
"""

ppt_prompt = """
## Reference info
You are an assistant with name as "TB Guru".
We have generated a PPT for the user and the link is attached below, tell the user to download it.
If the PPT link is empty, tell the user that we cannot generate PPT now. Please ask them to try again later.

## PPT link
{ppt_link}

## INSTRUCT
now, reply your result.
"""


class WcsDataQuery(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.tmp_file_dir = "./tmp/wcs"

    def get_name(self) -> str:
        return "wcs_data_query"

    def _generate_ppt(self, data: list[SearchItem], insight: str) -> str:
        file_dir = f"{self.tmp_file_dir}/{str(uuid.uuid4())}"
        os.makedirs(file_dir, exist_ok=True)
        image_paths = [f"{file_dir}/image1.png", f"{file_dir}/image2.png"]
        ppt_path = f"{file_dir}/ppt.pptx"
        df = pd.DataFrame([w.model_dump() for w in data])
        plot_graph(df, "wcs_data_query", "days", image_paths[0])
        plot_graph(df, "wcs_data_query", "days", image_paths[1])
        df = df.drop(columns=["days", "meta__score", "meta__reference", "id"])
        ppt_generation(
            df, llm_insight=insight, company_name=data[0].company, image_paths=image_paths, output_path=ppt_path
        )
        files = [
            ("files", ("tb_guru_ppt.pptx", open(ppt_path, "rb"), UploadFileContentType.PPTX)),
        ]
        links = self.unified_search.upload_file_to_minio(files)
        shutil.rmtree(file_dir)
        return links[0] if links else ""

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

        wcs_data = search_res[0].items

        final_prompt = prompt.format(
            user_input=context.conversation.current_user_input,
            wcs_data="\n".join([item.model_dump_json() for item in wcs_data]),
        )
        logger.info(f"final prompt: {final_prompt}")
        result = chat_model.chat(final_prompt, max_length=1024).response
        logger.info(f"chat result: {result}")

        is_ppt_output = context.conversation.get_simplified_entities()["is_ppt_output"]
        if is_ppt_output and wcs_data:
            ppt_link = self._generate_ppt(wcs_data, result)
            final_prompt = ppt_prompt.format(ppt_link=ppt_link)
            logger.info(f"ppt prompt: {final_prompt}")
            result = chat_model.chat(final_prompt, max_length=1024).response
            logger.info(f"chat result: {result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
