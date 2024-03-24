import asyncio
import configparser
import json
import logging
import multiprocessing
import os
import traceback
from typing import Optional
from urllib.request import Request

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, Form, Depends
from gluon_meson_sdk.models.longging.pg_log_service import PGModelLogService
from gluon_meson_sdk.models.exceptions import TokenLimitExceededException, ChatModelRequestException
from loguru import logger
from sse_starlette import EventSourceResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from uvicorn import run

from action.base import ErrorResponse, AttachmentResponse, JumpOutResponse, ActionResponse, ChatResponseAnswer
from dialog_manager.base import BaseDialogManager, DialogManagerFactory
from emailbot.emailbot import get_config, EmailBot, EmailBotSettings
from logging_intercept_handler import InterceptHandler
from promptflow.command import ScoreCommand
from router import api_router
from third_system.atom_service import AtomService
from third_system.microsoft_graph import Graph
from third_system.unified_search import UnifiedSearch
from utils.common import get_value_or_default_from_dict

config = configparser.ConfigParser()
config.read("config.ini")
load_dotenv()

is_local_mode = os.environ.get("ENV", "").lower() == "local"

log_handler = [
    {
        "sink": "logs/log_{time}.log",
        "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} {level} {message}",
        "serialize": True,
        "rotation": "2days",
        "retention": "1 week",
    }
]

app = FastAPI()


def get_app() -> FastAPI:
    app.include_router(api_router)
    init_logging()
    return app


def init_logging():
    intercept_handler = InterceptHandler()
    logging.getLogger("uvicorn").handlers = [intercept_handler]
    logging.getLogger("uvicorn.access").handlers = [intercept_handler]
    logging.root.handlers = [intercept_handler]
    if not is_local_mode:
        logger.configure(handlers=log_handler, extra={"application_name": "thought agent"})


dialog_manager: BaseDialogManager = DialogManagerFactory.create_dialog_manager()

if is_local_mode:
    origins = [
        "http://127.0.0.1",
        "http://127.0.0.1:8089",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as err:
        err_msg = f"Error occurred: {err}"
        logger.info(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(code=500, message=err_msg, answer={}, jump_out_flag=True).__dict__,
        )


@app.post("/chat/")
def chat(
    user_input: str = Form(), session_id: Optional[str] = Form(None), files: Optional[list[UploadFile]] = Form(None)
):
    result, conversation = dialog_manager.handle_message(user_input, session_id, files)
    # if config.get('debugMode', 'debug') == "True":
    #     return {"response": result, "conversation": conversation, "session_id": conversation.session_id}
    return {"response": result, "session_id": conversation.session_id}


async def generate_answer_with_len_limited(answer, **kwargs):
    # chunk with 500
    for i in range(0, len(answer), 1000):
        yield {"data": json.dumps({"answer": answer[i : i + 1000], **kwargs})}


async def parse_file_name(file_url):
    return file_url.split("/")[-1]


@app.post("/score/")
async def score(
    score_command: ScoreCommand,
    unified_search: UnifiedSearch = Depends(),
    atom_service: AtomService = Depends(),
):
    """
    This api is a chat entrypoint, for adapt prompt flow protocol, we use the name score
    """
    err_msg = ""
    result = None
    conversation = None
    session_id = score_command.conversation_id
    user_id = score_command.user_id
    file_urls = []
    if score_command.file_urls:
        file_urls = score_command.file_urls
    elif score_command.file_url:
        file_urls = [score_command.file_url]

    if score_command.from_email:
        await atom_service.create_human_message(session_id, user_id, score_command.question)

    try:
        first_file = (
            await unified_search.download_raw_file_from_minio(file_urls[0]) if file_urls and file_urls[0] else None
        )
        result, conversation = await dialog_manager.handle_message(
            message=score_command.question,
            session_id=session_id,
            first_file_name=await parse_file_name(file_urls[0]) if first_file else None,
            file_urls=file_urls,
            is_email_request=score_command.from_email,
        )
    except Exception as err:
        logger.info(traceback.format_exc())
        if conversation:
            conversation.reset_history()

        if isinstance(err, TokenLimitExceededException):
            err_msg = "Dear user, your input has exceeded the allowed token numbers." + err.message.split(":")[
                1
            ].replace("This model's maximum context length is", "We allow")
            err_msg = (
                err_msg.replace("Your messages has exceeded the model's maximum context length. ", "") + " Thanks."
            )
        elif isinstance(err, ChatModelRequestException):
            if err.model_source == "HSBC":
                err_msg = "Ops.... share platform broke down, please contact your IT team for further assistance."
            else:
                err_msg = "Ops.... GM model broke down, please contact your IT team for further assistance."
        else:
            err_msg = "Ops.... seems we hit problem to serve you, please contact your IT team for further assistance."

    async def generator():
        if not result:
            answer = {"answer": err_msg if err_msg else "unknown error occurred"}
        elif isinstance(result, JumpOutResponse):
            answer = {"answer": "Sorry, I can't help you with that."}
        else:
            answer = {
                "answer": result.answer.get_content_with_extra_info(from_email=score_command.from_email),
                "session_id": session_id,
                **(
                    dict(attachments=[a.model_dump_json() for a in result.attachments])
                    if isinstance(result, AttachmentResponse)
                    else {}
                ),
            }
        if score_command.from_email:
            origin_answer = result.answer if isinstance(result, ActionResponse) else None
            ai_message = await atom_service.create_ai_message(
                session_id,
                user_id,
                message=origin_answer.content if isinstance(origin_answer, ChatResponseAnswer) else None,
                prompt_message=answer,
            )
            feedback_link = (
                atom_service.generate_feedback_link(ai_message["id"])
                if ai_message and "id" in ai_message and ai_message["id"]
                else None
            )
            if feedback_link:
                answer["answer"] += f"<br><a href='{feedback_link}'>Click here to share your feedback with us!</a>"

        async for answer in generate_answer_with_len_limited(**answer):
            yield answer
        full_history = []
        if conversation is not None:
            full_history = conversation.history.format_messages()
        await asyncio.sleep(0.1)
        asyncio.create_task(
            PGModelLogService().async_log(
                session_id,
                "overall",
                "no_model",
                full_history[:-1] if len(full_history) > 0 else [],
                full_history[-1]["content"] if len(full_history) > 0 and "content" in full_history[-1] else "",
                {**score_command.model_dump(), "extra_info": result.answer.extra_info if result else {}},
                err_msg,
            )
        )

    return EventSourceResponse(generator())


@app.get("/healthy/")
async def healthcheck():
    return {"status": "alive"}


async def start_emailbot():
    logger.info("Starting emailbot")
    emailbot_configuration = get_config(EmailBotSettings)
    graph = await Graph()
    bot = EmailBot(emailbot_configuration, graph)
    await bot.periodically_call_api()


def run_child_process():
    logging.root.handlers = [InterceptHandler()]
    logger.configure(handlers=log_handler, extra={"application_name": "thought agent", "process": "emailbot"})
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(start_emailbot())
    except asyncio.CancelledError:
        pass


def main():
    if get_value_or_default_from_dict(os.environ, "START_EMAILBOT", "").lower() == "true":
        child_process = multiprocessing.Process(target=run_child_process)
        child_process.start()

    if is_local_mode:
        run(
            "app:app",
            host="0.0.0.0",
            port=7788,
            reload=True,
            reload_dirs=os.path.dirname(os.path.abspath(__file__)),
        )
    else:
        run("app:get_app", host="0.0.0.0", port=7788)


if __name__ == "__main__":
    # session_id = "123"
    # user_input = "天气好"
    # result, conversation = dialog_manager.handle_message(user_input, session_id)
    main()
