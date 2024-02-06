import asyncio
import configparser
import json
import multiprocessing
import os
import traceback
from typing import Optional
from urllib.request import Request

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, Form, Depends
from gluon_meson_sdk.models.longging.pg_log_service import PGModelLogService
from loguru import logger
from sse_starlette import EventSourceResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from uvicorn import run

from action.base import ErrorResponse, AttachmentResponse, JumpOutResponse
from dialog_manager.base import BaseDialogManager, DialogManagerFactory
from emailbot.emailbot import get_config, EmailBot, EmailBotSettings
from promptflow.command import ScoreCommand
from router import api_router
from third_system.microsoft_graph import Graph
from third_system.unified_search import UnifiedSearch
from utils.utils import get_value_or_default_from_dict

config = configparser.ConfigParser()
config.read("config.ini")
load_dotenv()

app = FastAPI()
app.include_router(api_router)
dialog_manager: BaseDialogManager = DialogManagerFactory.create_dialog_manager()

if os.getenv("LOCAL_MODE") == "1":
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


@app.post("/score/")
async def score(
    score_command: ScoreCommand,
    unified_search: UnifiedSearch = Depends(),
):
    """
    This api is a chat entrypoint, for adapt prompt flow protocol, we use the name score
    """
    err_msg = ""
    result = None
    conversation = None
    session_id = score_command.conversation_id
    file_urls = []
    if score_command.file_urls:
        file_urls = score_command.file_urls
    elif score_command.file_url:
        file_urls = [score_command.file_url]

    try:
        file_res = [await unified_search.download_file_from_minio(url) for url in file_urls]
        result, conversation = await dialog_manager.handle_message(
            score_command.question,
            session_id,
            file_contents=file_res if file_res else None,
            is_email_request=score_command.from_email,
        )
    except Exception as err:
        logger.info(traceback.format_exc())
        if conversation:
            conversation.reset_history()
        err_msg = f"Error occurred: {err}, please try again later."

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
                    dict(attachment=result.attachment.model_dump_json())
                    if isinstance(result, AttachmentResponse)
                    else {}
                ),
            }

        async for answer in generate_answer_with_len_limited(**answer):
            yield answer
        full_history = []
        if conversation is not None:
            full_history = conversation.history.format_messages()
        await PGModelLogService().async_log(
            session_id,
            "overall",
            "no_model",
            full_history[:-1] if len(full_history) > 0 else [],
            full_history[-1]["content"] if len(full_history) > 0 and "content" in full_history[-1] else "",
            {**score_command.model_dump(), "extra_info": result.answer.extra_info if result else {}},
            err_msg,
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

    if os.getenv("LOCAL_MODE") == "1":
        run(
            "app:app",
            host="0.0.0.0",
            port=7788,
            reload=True,
            reload_dirs=os.path.dirname(os.path.abspath(__file__)),
        )
    else:
        run("app:app", host="0.0.0.0", port=7788)


if __name__ == "__main__":
    # session_id = "123"
    # user_input = "天气好"
    # result, conversation = dialog_manager.handle_message(user_input, session_id)
    main()
