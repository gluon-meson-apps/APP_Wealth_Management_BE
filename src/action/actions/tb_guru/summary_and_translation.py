import os
import shutil
import uuid

import tiktoken
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
    result = (
        await chat_model.achat(
            **chat_message_preparation.to_chat_params(),
            max_length=MAX_OUTPUT_TOKEN_SiZE,
            sub_scenario=f"sub_part_{index}",
        )
    ).response
    return result


class SummarizeAndTranslate(TBGuruAction):
    def __init__(self) -> None:
        super().__init__()
        self.enc = tiktoken.encoding_for_model("gpt-4")
        self.tmp_file_dir = os.path.join(os.path.dirname(__file__), "../../../../", "tmp/txt")

    def get_name(self) -> str:
        return "summary_and_translation"

    async def save_answer_to_file(self, origin_file_name, answer) -> list[Attachment]:
        files_dir = f"{self.tmp_file_dir}/{str(uuid.uuid4())}"
        os.makedirs(files_dir, exist_ok=True)
        file_name = f"{origin_file_name.split('.')[0]}.txt"
        file_path = f"{files_dir}/{file_name}"
        with open(file_path, "w") as f:
            f.write(answer)
        files = [Attachment(name=file_name, path=file_path, content_type=UploadFileContentType.TXT)]
        links = await self.unified_search.upload_file_to_minio(files)
        shutil.rmtree(files_dir)
        for index, f in enumerate(files):
            f.url = links[index] if links else ""
        return files

    async def loop_ask(self, user_input, file_contents, chat_model):
        processed_data = ""
        part = 0
        while True:
            current_result = await ask_chatbot(user_input, file_contents, part, chat_model, processed_data)
            processed_data += current_result
            logger.info(f"part {part} result: {current_result}")
            if len(self.enc.encode(current_result)) < MAX_OUTPUT_TOKEN_SiZE:
                break
            part += 1
        return processed_data

    async def run(self, context: ActionContext) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)

        user_input = context.conversation.current_user_input
        input_token_size = len(self.enc.encode(user_input))

        if input_token_size > MAX_OUTPUT_TOKEN_SiZE:
            return GeneralResponse(
                code=200,
                message="success",
                answer=f"Sorry, your input have {input_token_size} tokens but the maximum limit for the input is {MAX_OUTPUT_TOKEN_SiZE} tokens. Please put the parts that need to be translated or summarized in a TXT file and upload it as an attachment.",
                jump_out_flag=False,
            )

        file = await self.download_first_raw_file(context)
        file_contents = file.contents if file else ""
        file_token_size = len(self.enc.encode(file.contents)) if file else 0

        logger.info(f"file token size: {file_token_size}")

        if file_token_size > MAX_FILE_TOKEN_SIZE:
            return GeneralResponse(
                code=200,
                message="success",
                answer=f"Sorry, your file have {file_token_size} tokens but the maximum limit for the file is {MAX_FILE_TOKEN_SIZE} tokens. Please upload a smaller file.",
                jump_out_flag=False,
            )

        if file_token_size + input_token_size <= MAX_OUTPUT_TOKEN_SiZE:
            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message(
                "user",
                direct_prompt,
                user_input=user_input + "\n\n" + file_contents,
            )
            # chat_message_preparation.log(logger)
            result = (
                await chat_model.achat(
                    **chat_message_preparation.to_chat_params(),
                    max_length=MAX_OUTPUT_TOKEN_SiZE,
                )
            ).response
            logger.info(f"final direct result: {result}")
        else:
            result = await self.loop_ask(context.conversation.current_user_input, file_contents, chat_model)
            logger.info(f"result token size: {len(self.enc.encode(result))}")
            logger.info(f"final loop result: {result}")

        if file_token_size > 0:
            attachments = await self.save_answer_to_file(file.name, result)
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content="Please check attachments for all the replies.",
                intent=context.conversation.current_intent.name,
            )
            return AttachmentResponse(
                code=200, message="success", answer=answer, jump_out_flag=False, attachments=attachments
            )

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
