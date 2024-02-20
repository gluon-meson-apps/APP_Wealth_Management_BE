import asyncio

import pandas as pd
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import (
    Action,
    ActionResponse,
    ResponseMessageType,
    ChatResponseAnswer,
    AttachmentResponse,
    Attachment,
    UploadFileContentType,
    GeneralResponse,
    UploadStorageFile,
)
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter

from action.df_processor import DfProcessor
from third_system.search_entity import SearchParam, SearchResponse
from third_system.unified_search import UnifiedSearch
from tracker.context import ConversationContext

prompt = """## Role
you are a chatbot, you need to answer the question from user

## context

{{context_info}}

## user input

{{user_input}}

## INSTRUCT

based on the context, answer the question;

"""


class FileBatchAction(Action):
    def __init__(self):
        self.unified_search: UnifiedSearch = UnifiedSearch()
        self.df_processor: DfProcessor = DfProcessor()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

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
            if not response or not response[0].items:
                return result, context_info, source_name

            first_result = response[0].items[0]
            faq_answer_column = "meta__answers"
            # todo: if faq score is too low should drop it.
            if faq_answer_column in first_result.meta__reference.model_extra:
                score_threshold = 0.82
                if first_result.meta__score < score_threshold:
                    question_header = "=" * 10 + "question" + "=" * 10
                    search_result_header = "=" * 10 + "search result question" + "=" * 10
                    logger.warning(
                        f"score is too low: {first_result.meta__score} < {score_threshold} for: \n"
                        f"{question_header}\n{question}\n{search_result_header}\n"
                        f"{first_result.meta__reference.model_extra[faq_answer_column]}"
                    )
                    return result, context_info, source_name
                result = first_result.meta__reference.model_extra[faq_answer_column]
                context_info = first_result.model_extra["text"]
                source_name = first_result.meta__reference.meta__source_name
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

            return result, context_info, source_name

        return get_result_from_llm

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        conversation: ConversationContext = context.conversation
        if len(conversation.uploaded_file_urls) == 0:
            return GeneralResponse.normal_failed_text_response(
                "No file uploaded, please upload a file and try again.", conversation.current_intent.name
            )
        available_tags = ["context", "product_line", "country"]
        tags = {k: v for k, v in conversation.get_simplified_entities().items() if k in available_tags}
        logger.info(f"tags: {tags}")
        file_contents = await self.unified_search.download_file_from_minio(conversation.uploaded_file_urls[0])
        df = self.df_processor.search_items_to_df(file_contents.items)
        questions_column_entity = conversation.get_entity_by_name("questions_column_name")
        questions_column = questions_column_entity.value.lower() if questions_column_entity else "questions"
        if questions_column not in df.columns:
            return GeneralResponse.normal_failed_text_response(
                f"No header named {questions_column} found in file. please modify your file to add a {questions_column} header and upload again, or you can provide another column header name you want to use as questions column.",
                conversation.current_intent.name,
            )
        df = df[df[questions_column].notna()].reset_index()

        chat_model = self.scenario_model_registry.get_model(self.scenario_model, conversation.session_id)
        get_result_from_llm = self.get_function_with_chat_model(chat_model, {"basic_type": "faq", **tags}, conversation)
        tasks = [
            get_result_from_llm(row[questions_column], index) for index, row in enumerate(df.to_dict(orient="records"))
        ]
        search_res = await asyncio.gather(*tasks)
        search_df = pd.DataFrame(search_res, columns=["answers", "reference_data", "reference_name"])
        df = df[[questions_column]].merge(search_df, left_index=True, right_index=True, how="left").reset_index()
        df = df[[questions_column, "answers", "reference_name", "reference_data"]]

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content="Already replied all questions in file",
            intent=conversation.current_intent.name,
        )

        file_name = f"{conversation.session_id}.csv"
        file_path = f"/tmp/{file_name}"
        content_type = UploadFileContentType.CSV
        df.to_csv(file_path, index=False)
        files = [UploadStorageFile(filename=file_name, file_path=file_path, content_type=content_type)]
        urls = await self.unified_search.upload_file_to_minio(files)
        attachment = Attachment(path=file_path, name=file_name, content_type=content_type, url=urls[0])

        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachment=attachment
        )
