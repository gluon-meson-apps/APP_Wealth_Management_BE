import asyncio
import os

import pandas as pd
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation, ChatMessage
from loguru import logger

from action.base import (
    ActionResponse,
    ResponseMessageType,
    ChatResponseAnswer,
    AttachmentResponse,
    Attachment,
    UploadFileContentType,
    GeneralResponse,
)
from action.actions.tb_guru.base import TBGuruAction
from action.df_processor import DfProcessor
from third_system.search_entity import SearchParam, SearchResponse
from tracker.context import ConversationContext
from utils.common import generate_tmp_dir

MAX_ROW_COUNT = 50
MA_ROW_EXCEED_MSG = """
Dear user, your first {{max_row}} questions has been answered.
We are sorry your question count has reached the system capacity, we can not answer the questions after the {{max_row}}th.
Please put them into another request, we will serve you there.”
"""

prompt = """## Role
you are a chatbot, you need to answer the question from user

## context

{{context_info}}

## user input

{{user_input}}

## INSTRUCT

based on the context, answer the question;

"""


class FileBatchAction(TBGuruAction):
    def __init__(self):
        super().__init__()
        self.df_processor: DfProcessor = DfProcessor()
        self.tmp_file_dir = generate_tmp_dir("batch_qa")
        os.makedirs(self.tmp_file_dir, exist_ok=True)

    def get_name(self) -> str:
        return "file_batch_qa"

    def get_function_with_chat_model(self, chat_model, tags, conversation):
        async def get_result_from_llm(question, index):
            response: list[SearchResponse] = await self.unified_search.search(
                SearchParam(query=question, tags=tags), conversation.session_id
            )
            logger.info(f"search response: {response}")
            context_info = "can't find any result"
            source_name = ""
            result = "no information found, not able to answer"
            score = None
            if not response or not response[0].items:
                return result, context_info, source_name, score

            first_result = response[0].items[0]
            faq_answer_column = "meta__answers"
            # todo: if faq score is too low should drop it.
            if faq_answer_column in first_result.meta__reference.model_extra:
                result = first_result.meta__reference.model_extra[faq_answer_column]
                context_info = first_result.model_extra["text"]
                source_name = first_result.meta__reference.meta__source_name
                score = first_result.meta__score
            else:
                context_info = "\n".join([item.model_dump_json() for item in response])
                chat_message_preparation = ChatMessagePreparation()
                chat_message_preparation.add_message(
                    "system",
                    prompt,
                    context_info=context_info,
                    user_input=question,
                )
                chat_message_preparation.log(logger)

                result = (
                    await chat_model.achat(
                        **chat_message_preparation.to_chat_params(), max_length=2048, sub_scenario=index
                    )
                ).response
                logger.info(f"chat result: {result}")

                source_name = "\n".join(
                    {item.meta__reference.meta__source_name for one_response in response for item in one_response.items}
                )

                score = "\n".join({str(item.meta__score) for one_response in response for item in one_response.items})

            return result, context_info, source_name, score

        return get_result_from_llm

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        first_file = await self.download_first_processed_file(context)
        if not first_file:
            return GeneralResponse.normal_failed_text_response(
                "No valid file uploaded, please upload a valid file and try again.",
                context.conversation.current_intent.name,
            )

        conversation: ConversationContext = context.conversation
        available_tags = ["context", "product_line", "country"]
        tags = {k: v for k, v in conversation.get_simplified_entities().items() if k in available_tags}
        logger.info(f"tags: {tags}")
        df = self.df_processor.search_items_to_df(first_file.items)
        questions_column_entity = conversation.get_entity_by_name("questions_column_name")
        questions_column = questions_column_entity.value.lower() if questions_column_entity else "questions"
        if questions_column not in df.columns:
            return GeneralResponse.normal_failed_text_response(
                f"No header named {questions_column} found in file. please modify your file to add a {questions_column} header and upload again, or you can provide another column header name you want to use as questions column.",
                conversation.current_intent.name,
            )

        df = df[df[questions_column].notna()].reset_index()

        answer_msg = (
            ChatMessage.format_jinjia_template(MA_ROW_EXCEED_MSG, max_row=MAX_ROW_COUNT)
            if df.shape[0] > MAX_ROW_COUNT
            else "Already replied all questions in file"
        )
        # Only process the first 50 rows
        answer_df = df.iloc[:MAX_ROW_COUNT, :]

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, conversation.session_id)
        get_result_from_llm = self.get_function_with_chat_model(chat_model, {"basic_type": "faq", **tags}, conversation)
        tasks = [
            get_result_from_llm(row[questions_column], index)
            for index, row in enumerate(answer_df.to_dict(orient="records"))
        ]
        search_res = await asyncio.gather(*tasks)
        search_df = pd.DataFrame(search_res, columns=["answers", "reference_question", "reference_name", "score"])
        search_df["reference_answer"] = search_df["answers"]
        df = df[[questions_column]].merge(search_df, left_index=True, right_index=True, how="left").reset_index()
        df = df[[questions_column, "answers", "reference_name", "reference_question", "reference_answer", "score"]]

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=answer_msg,
            intent=conversation.current_intent.name,
        )

        file_name = f"{conversation.session_id}.xlsx"
        file_path = os.path.join(self.tmp_file_dir, file_name)
        df.to_excel(file_path, index=False)
        attachment = Attachment(name=file_name, path=file_path, content_type=UploadFileContentType.XLSX)
        urls = await self.unified_search.upload_files_to_minio([attachment])
        attachment.url = urls[0]

        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachments=[attachment]
        )
