import asyncio
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
    UploadStorageFile,
)
from third_system.search_entity import SearchParam, SearchItem
from third_system.unified_search import UnifiedSearch
from utils.ppt_helper import generate_ppt
from utils.utils import extract_json_from_code_block

report_filename = "file_validation_report.html"

extract_data_prompt = """
## Role
You are an assistant with name as "TB Guru".
Help me extract data from user input and reply it with below JSON schema.

## Schema should be like this
{
    // all years data for specific company which should be mentioned in user input
    "all_years_data": [{
        "company": "company name", // STRING
        "days": "the date for the record", // STRING
        "dpo": "DPO", // NUMBER,
        "dso": "DSO", // NUMBER,
        "dio": "DIO", // NUMBER,
        "ccc": "CCC", // NUMBER,
    }, ...],
    // latest year data for all companies
    "latest_year_data": [{
        "company": "company name", // STRING
        "days": "the date for the record", // STRING
        "dpo": "DPO", // NUMBER,
        "dso": "DSO", // NUMBER,
        "dio": "DIO", // NUMBER,
        "ccc": "CCC", // NUMBER,
    }, ...]
}

## User input
{{user_input}}

## Instruction
Please reply the formatted JSON data.
"""

user_prompt = """
## User question
{{user_input}}
Please IGNORE my requirements for PPT and DO NOT mention anything about PPT in your reply.
"""

ppt_prompt = """
## Info
{{info}}

## Requirements
You are an assistant with name as "TB Guru".
You have generated a PPT for the user and the link is attached below, tell the user to download it.
If the PPT link is empty, ask the user to check if their input question is valid.

## PPT link
{{ppt_link}}

## Instruction
now, reply your result with above info.
"""


def extract_data(context, chat_model) -> tuple[list[SearchItem], list[SearchItem]]:
    chat_message_preparation = ChatMessagePreparation()
    chat_message_preparation.add_message(
        "system",
        extract_data_prompt,
        user_input=context.conversation.current_user_input,
    )
    chat_message_preparation.log(logger)

    result = chat_model.chat(
        **chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="data_provided"
    ).response
    formatted_data = extract_json_from_code_block(result)
    current_company_data = formatted_data["all_years_data"] if "all_years_data" in formatted_data else []
    latest_all_data = formatted_data["latest_year_data"] if "latest_year_data" in formatted_data else []
    logger.info(f"formatted data: {formatted_data}")
    return [SearchItem(meta__score=-1, **d) for d in latest_all_data], [
        SearchItem(meta__score=-1, **d) for d in current_company_data
    ]


def parse_model_to_dataframe(data):
    df = pd.DataFrame([w.model_dump() for w in data])
    return df.drop(columns=["meta__score", "meta__reference", "id"], errors="ignore")


class WcsDataQuery(Action):
    def __init__(self):
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"
        self.tmp_file_dir = os.path.join(os.path.dirname(__file__), "../../../../", "tmp/wcs")

    def get_name(self) -> str:
        return "wcs_data_query"

    async def _generate_ppt_link(self, df_current: pd.DataFrame, df_all: pd.DataFrame, insight: str) -> str:
        files_dir = f"{self.tmp_file_dir}/{str(uuid.uuid4())}"
        ppt_path = generate_ppt(df_current, df_all, insight, files_dir)
        if ppt_path:
            files = [
                UploadStorageFile(
                    filename="tb_guru_ppt.pptx", file_path=ppt_path, content_type=UploadFileContentType.PPTX
                )
            ]
            links = await self.unified_search.upload_file_to_minio(files)
            shutil.rmtree(files_dir)
            return links[0] if links else ""
        return ""

    async def _search_db(self, entity_dict, session_id) -> tuple[list[SearchItem], list[SearchItem]]:
        query_list = [
            f"""Query WCS data with days as {entity_dict["days"]}:"""
            if "days" in entity_dict
            else "Query WCS data sort by days descending:"
        ]
        if "company" in entity_dict:
            query_list.append(f"""Query WCS data with company {entity_dict["company"]}:""")
        tasks = [self.unified_search.search(SearchParam(query=q), session_id) for q in query_list]
        search_res = await asyncio.gather(*tasks)
        items = [s[0].items if s else [] for s in search_res]
        all_companies_data, current_company_data = items[0], items[1] if len(items) > 1 else []
        return all_companies_data, current_company_data

    async def run(self, context) -> ActionResponse:
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        logger.info(f"exec action: {self.get_name()} ")

        entity_dict = context.conversation.get_simplified_entities()
        is_ppt_output = entity_dict["is_ppt_output"] if "is_ppt_output" in entity_dict else False
        is_data_provided = entity_dict["is_data_provided"] if "is_data_provided" in entity_dict else False

        if is_data_provided:
            latest_all_data, current_company_data = extract_data(context, chat_model) if is_ppt_output else ([], [])
        else:
            latest_all_data, current_company_data = await self._search_db(entity_dict, context.conversation.session_id)

        df_current_company = parse_model_to_dataframe(current_company_data)
        df_all_companies = parse_model_to_dataframe(latest_all_data)

        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            user_prompt,
            user_input=context.conversation.current_user_input,
        )
        if not is_data_provided:
            chat_message_preparation.add_message(
                "assistant",
                """## WCS data are extracted already\n{{wcs_data}}""",
                wcs_data=pd.concat([df_current_company, df_all_companies], ignore_index=True).to_string(),
            )
        chat_message_preparation.log(logger)

        info_result = chat_model.chat(
            **chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="insight"
        ).response
        logger.info(f"chat result: {info_result}")

        final_result = info_result
        if is_ppt_output:
            ppt_link = await self._generate_ppt_link(df_current_company, df_all_companies, info_result)

            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message("system", ppt_prompt, ppt_link=ppt_link, info=info_result)
            chat_message_preparation.log(logger)

            final_result = chat_model.chat(
                **chat_message_preparation.to_chat_params(), max_length=1024, sub_scenario="ppt"
            ).response

        logger.info(f"final result: {final_result}")

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=final_result,
            intent=context.conversation.current_intent.name,
            references=[] if is_data_provided else current_company_data + latest_all_data,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)


if __name__ == "__main__":
    file_dir = os.path.join(os.path.dirname(__file__), "../../../../", "tmp/wcs")
    with open(f"{file_dir}/test.txt", "w") as f:
        f.write("test")
