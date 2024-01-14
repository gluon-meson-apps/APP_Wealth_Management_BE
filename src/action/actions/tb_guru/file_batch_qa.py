from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger
from io import StringIO
import pandas as pd

from action.base import (
    Action,
    ActionResponse,
    ResponseMessageType,
    ChatResponseAnswer,
    AttachmentResponse,
    Attachment,
    UploadFileContentType,
)
from gluon_meson_sdk.models.scenario_model_registry.base import DefaultScenarioModelRegistryCenter
from third_system.search_entity import SearchParam
from third_system.unified_search import UnifiedSearch


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
        self.unified_search = UnifiedSearch()
        self.scenario_model_registry = DefaultScenarioModelRegistryCenter()
        self.scenario_model = self.get_name() + "_action"

    def get_name(self) -> str:
        return "file_batch_qa"

    def get_function_with_chat_model(self, chat_model, context):
        def get_result_from_llm(self, question):
            response = self.unified_search.vector_search(SearchParam(query=question), "faq")
            logger.info(f"search response: {response}")
            context_info = "\n".join([item.json() for item in response])

            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message(
                "user",
                prompt,
                context_info=context_info,
                user_input=question,
            )
            chat_message_preparation.log(logger)

            result = chat_model.chat(**chat_message_preparation.to_chat_params(), max_length=2048).response
            logger.info(f"chat result: {result}")

            return result

        return get_result_from_llm

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")

        TESTDATA = StringIO(context.conversation.uploaded_file_contents[0].items[0].text)

        df = pd.read_csv(TESTDATA, sep=";")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        get_result_from_llm = self.get_function_with_chat_model(chat_model, context)
        df["answer"] = df.apply(lambda row: get_result_from_llm(self, row["questions"]), axis=1)

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content="Already replied all questions in file",
            intent=context.conversation.current_intent.name,
        )

        file_name = f"{context.conversation.session_id}.csv"
        file_path = f"/tmp/{file_name}"
        content_type = UploadFileContentType.CSV
        df.to_csv(file_path, index=False)
        files = [
            ("files", (file_name, open(file_path), content_type)),
        ]
        urls = self.unified_search.upload_file_to_minio(files)
        attachment = Attachment(path=file_path, name=file_name, content_type=content_type, url=urls[0])

        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachment=attachment
        )
