import asyncio
import os
import shutil
import uuid

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
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
from utils.utils import generate_tmp_dir

MAX_OUTPUT_TOKEN_SiZE = 4096
MAX_FILE_TOKEN_SIZE = 64 * 1024

direct_prompt = """## Role
You are a helpful assistant with name as "TB Guru", you need to answer the user's question.

## User input
{{user_input}}

## Attention
If the user asks for a summary, please provide a summary less than 3000 words.
"""

loop_prompt = """## Role
You are a helpful assistant with name as "TB Guru", you need to answer the user's question.

## User input
{{user_input}}

## Contents to be processed
{{file_contents}}

## Attention
If the user asks for a summary, please provide a summary less than 3000 words.
"""


async def ask_chatbot(user_input, file_contents, index, chat_model, processed_data=None):
    chat_message_preparation = ChatMessagePreparation()
    chat_message_preparation.add_message("user", loop_prompt, user_input=user_input, file_contents=file_contents)
    if processed_data:
        chat_message_preparation.add_message(
            "assistant",
            """## Already processed parts\n{{processed_data}}""",
            processed_data=processed_data,
        )
    # chat_message_preparation.log(logger)
    logger.info(f"start part {index}")
    result = (
        await chat_model.achat(
            **chat_message_preparation.to_chat_params(),
            max_length=MAX_OUTPUT_TOKEN_SiZE,
            sub_scenario=f"sub_part_{index}",
        )
    ).response
    return result


def save_answer_to_file(files_dir, origin_file_name, answer) -> Attachment:
    file_name = f"{origin_file_name.split('.')[0]}.txt"
    file_path = f"{files_dir}/{file_name}"
    with open(file_path, "w") as f:
        f.write(answer)
    return Attachment(name=file_name, path=file_path, content_type=UploadFileContentType.TXT)


async def loop_ask(user_input, file: Attachment, chat_model) -> str:
    file_token_size = chat_model.get_encode_length(file.contents)
    logger.info(f"file {file.name} token size: {file_token_size}")
    if file_token_size > MAX_FILE_TOKEN_SIZE:
        return f"Sorry, the file has {file_token_size} tokens but the maximum limit for the file is {MAX_FILE_TOKEN_SIZE} tokens. Please upload a smaller file."
    processed_data = ""
    part = 0
    while True:
        current_result = await ask_chatbot(user_input, file, part, chat_model, processed_data)
        processed_data += current_result
        part_token_size = chat_model.get_encode_length(current_result)
        logger.info(f"part {part} token_size: {part_token_size}")
        logger.info(f"part {part} result: {current_result}")
        if part_token_size < MAX_OUTPUT_TOKEN_SiZE:
            logger.info(f"loop ended after part {part}")
            break
        part += 1
    return processed_data


class SummarizeAndTranslate(TBGuruAction):
    def __init__(self) -> None:
        super().__init__()
        self.tmp_file_dir = generate_tmp_dir("txt")

    def get_name(self) -> str:
        return "summary_and_translation"

    async def save_answers_to_files(self, origin_files: list[Attachment], answer: list[str]) -> list[Attachment]:
        files_dir = f"{self.tmp_file_dir}/{str(uuid.uuid4())}"
        os.makedirs(files_dir, exist_ok=True)
        files = [save_answer_to_file(files_dir, f.name, answer[index]) for index, f in enumerate(origin_files)]
        links = await self.unified_search.upload_file_to_minio(files)
        shutil.rmtree(files_dir)
        for index, f in enumerate(files):
            f.url = links[index] if links else ""
        return files

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input
        input_token_size = chat_model.get_encode_length(user_input)

        if input_token_size > MAX_OUTPUT_TOKEN_SiZE:
            return GeneralResponse(
                code=200,
                message="success",
                answer=f"Sorry, your input have {input_token_size} tokens but the maximum limit for the input is {MAX_OUTPUT_TOKEN_SiZE} tokens. Please put the parts that need to be translated or summarized in a TXT file and upload it as an attachment.",
                jump_out_flag=False,
            )

        files = await self.download_raw_files(context)
        available_files = [f for f in files if f]

        if not available_files:
            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message(
                "user",
                direct_prompt,
                user_input=user_input,
            )
            # chat_message_preparation.log(logger)
            result = (
                await chat_model.achat(
                    **chat_message_preparation.to_chat_params(), max_length=MAX_OUTPUT_TOKEN_SiZE, sub_scenario="direct"
                )
            ).response
            logger.info(f"final direct result: {result}")
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=result,
                intent=context.conversation.current_intent.name,
            )
            return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)

        tasks = [loop_ask(context.conversation.current_user_input, f, chat_model) for f in available_files]
        result = await asyncio.gather(*tasks)
        result_str = "\n".join(result)
        logger.info(f"final result token size: {chat_model.get_encode_length(result_str)}")
        logger.info(f"final loop result: {result_str}")

        attachments = await self.save_answers_to_files(available_files, result)
        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content="Please check attachments for all the replies.",
            intent=context.conversation.current_intent.name,
        )
        return AttachmentResponse(
            code=200, message="success", answer=answer, jump_out_flag=False, attachments=attachments
        )
