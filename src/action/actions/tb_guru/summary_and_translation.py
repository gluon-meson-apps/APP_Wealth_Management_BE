import asyncio

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation, ChatMessage
from loguru import logger

from action.actions.tb_guru.base import TBGuruAction
from action.base import (
    ActionResponse,
    GeneralResponse,
    ResponseMessageType,
    ChatResponseAnswer,
    UploadFileContentType,
    Attachment,
    AttachmentResponse,
)
from action.context import ActionContext
from third_system.search_entity import SearchItem
from tracker.context import ConversationContext
from utils.common import generate_tmp_dir, parse_str_to_bool

MAX_OUTPUT_TOKEN_SiZE = 3000
MAX_FILE_TOKEN_SIZE = 20 * 1024
ALLOW_FILE_TYPES = ["txt", "docx", "pdf", "doc"]
MINUTES_TO_GENERATE_FILE = 5

direct_prompt = """## Role
You are a helpful assistant with name as "TB Guru", you need to answer the user's question.

## User input
{{user_input}}

## Attention
If the user asks for a summary, please provide a summary less than 3000 words.
"""

file_prompt = """## Role
You are a helpful assistant with name as "TB Guru", you need to answer the user's question.

## User input
{{user_input}}

## Contents to be processed
{{file_contents}}

## Attention
If the user asks for a summary, please provide a summary less than 3000 words.
"""

FILE_ERROR_MSG = "The file is not available for processing. Please upload a valid file."

ONLY_1_FILE_TIP = (
    "\nPlease note, if you've uploaded multiple documents, we'll only process the first one at the moment."
)

FILE_GENERATING_MSG = """
We've initiated the file generation process, but it's may not yet accessible right now.
Please be aware, it may takes approximately {{minutes}} minutes for the file to be generated.
When the generating in progress, you will not get the .docx file from below link.
Once complete, you'll be able to download it using the provided link in the attachments to view the results.
"""

INPUT_TOKEN_EXCEED_MSG = """
Sorry, your input have {{input_token_size}} tokens but the maximum limit for the input is {{max_input_size}} tokens.
Please put the parts that need to be translated or summarized in a TXT, DOCX or PDF file and upload it as an attachment.
"""


def replace_file_type_to_docx(filename: str) -> str:
    file_type = filename.split(".")[-1]
    return filename.rsplit(f".{file_type}", 1)[0] + ".docx"


async def ask_chatbot(prompt, chat_model, sub_scenario):
    chat_message_preparation = ChatMessagePreparation()
    chat_message_preparation.add_message("user", prompt)
    # chat_message_preparation.log(logger)
    logger.info(f"start scenario {sub_scenario}")
    result = (
        await chat_model.achat(
            **chat_message_preparation.to_chat_params(),
            max_length=MAX_OUTPUT_TOKEN_SiZE,
            sub_scenario=sub_scenario,
        )
    ).response
    return result


def check_summary_needed(conversation: ConversationContext):
    entity_dict = conversation.get_simplified_entities()
    return parse_str_to_bool(entity_dict.get("is_summary_needed", False) if entity_dict else False)


async def split_file_to_ask(user_input, file_items: list[SearchItem], chat_model) -> str:
    logger.info("Will split files to ask LLM")

    if not file_items:
        return FILE_ERROR_MSG

    tasks = [
        ask_chatbot(
            ChatMessage.format_jinjia_template(file_prompt, user_input=user_input, file_contents=f.text),
            chat_model,
            f"sub_part_{index}",
        )
        for index, f in enumerate(file_items)
    ]
    result = await asyncio.gather(*tasks)
    return "\n".join(result) if result else FILE_ERROR_MSG


async def ask_bot_with_file(conversation: ConversationContext, file_items: list[SearchItem], chat_model) -> str:
    filename = file_items[0].meta__reference.meta__source_name
    file_contents = "\n".join([f.text for f in file_items])
    file_token_size = sum(
        [f.meta__reference.meta__token_size if f.meta__reference.meta__token_size else 0 for f in file_items]
    )
    logger.info(f"file {filename} token size: {file_token_size}")
    if file_token_size > MAX_FILE_TOKEN_SIZE:
        return f"Sorry, the file has {file_token_size} tokens but the maximum limit for the file is {MAX_FILE_TOKEN_SIZE} tokens. Please upload a smaller file."

    if check_summary_needed(conversation):
        logger.info("User asks for summary, will direct ask LLM")
        prompt = ChatMessage.format_jinjia_template(
            file_prompt, user_input=conversation.current_user_input, file_contents=file_contents
        )
        return await ask_chatbot(prompt, chat_model, "direct")
    return await split_file_to_ask(conversation.current_user_input, file_items, chat_model)


class SummarizeAndTranslate(TBGuruAction):
    def __init__(self) -> None:
        super().__init__()
        self.tmp_file_dir = generate_tmp_dir("txt")

    def get_name(self) -> str:
        return "summary_and_translation"

    async def save_answers_to_files(
        self, origin_files: list[list[SearchItem]], answer: list[str], file_urls: list[str] = None
    ) -> list[Attachment]:
        files = [
            Attachment(
                name=replace_file_type_to_docx(f[0].meta__reference.meta__source_name),
                path="",
                content_type=UploadFileContentType.DOCX,
                contents=answer[index],
                url=file_urls[index] if file_urls else None,
            )
            for index, f in enumerate(origin_files)
        ]
        file_tasks = list(map(self.unified_search.generate_new_file, files))
        new_file_urls = await asyncio.gather(*file_tasks)
        for index, f in enumerate(files):
            f.url = new_file_urls[index] if new_file_urls else ""
        return files

    async def ask_bot_with_files(
        self,
        conversation: ConversationContext,
        available_files: list[list[SearchItem]],
        chat_model,
        file_urls: list[str] = None,
    ) -> list[Attachment]:
        tasks = [ask_bot_with_file(conversation, f, chat_model) for f in available_files]
        result = await asyncio.gather(*tasks)
        result_str = "\n".join(result)
        logger.info(f"final result token size: {chat_model.get_encode_length(result_str)}")
        return await self.save_answers_to_files(available_files, result, file_urls)

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input
        input_token_size = chat_model.get_encode_length(user_input)

        if input_token_size > MAX_OUTPUT_TOKEN_SiZE:
            return GeneralResponse(
                code=200,
                message="success",
                answer=ChatResponseAnswer(
                    messageType=ResponseMessageType.FORMAT_TEXT,
                    content=ChatMessage.format_jinjia_template(
                        INPUT_TOKEN_EXCEED_MSG, input_token_size=input_token_size, max_input_size=MAX_OUTPUT_TOKEN_SiZE
                    ),
                    intent=context.conversation.current_intent.name,
                ),
                jump_out_flag=False,
            )

        # only process the first file
        raw_files = [await self.download_first_processed_file(context)]
        available_files = [
            f.items
            for f in raw_files
            if f and f.items and f.items[0].meta__reference.meta__source_type in ALLOW_FILE_TYPES
        ]

        if not available_files:
            result = await ask_chatbot(
                ChatMessage.format_jinjia_template(direct_prompt, user_input=user_input), chat_model, "direct"
            )
            logger.info(f"final direct result: {result}")
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=result,
                intent=context.conversation.current_intent.name,
            )
            return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)

        if context.conversation.is_email_request or check_summary_needed(context.conversation):
            attachments = await self.ask_bot_with_files(context.conversation, available_files, chat_model)
            message = "Please check attachments for all the replies."
        else:
            docx_names = [replace_file_type_to_docx(f[0].meta__reference.meta__source_name) for f in available_files]
            file_tasks = [self.unified_search.generate_file_link(name) for name in docx_names]
            file_urls = await asyncio.gather(*file_tasks)
            asyncio.create_task(self.ask_bot_with_files(context.conversation, available_files, chat_model, file_urls))
            attachments = [
                Attachment(name=name, path="", content_type=UploadFileContentType.DOCX, url=file_urls[index])
                for index, name in enumerate(docx_names)
            ]
            message = ChatMessage.format_jinjia_template(FILE_GENERATING_MSG, minutes=MINUTES_TO_GENERATE_FILE)
        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=message + ONLY_1_FILE_TIP if len(context.conversation.uploaded_file_urls) > 1 else message,
            intent=context.conversation.current_intent.name,
        )
        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachments=attachments
        )
