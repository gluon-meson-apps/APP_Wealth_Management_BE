import configparser
import json
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

from action.actions.tb_guru.email_reply import EmailReplyAction
from action.base import ErrorResponse, AttachmentResponse, JumpOutResponse
from action.context import ActionContext
from dialog_manager.base import BaseDialogManager, DialogManagerFactory
from promptflow.command import ScoreCommand
from router import api_router
from third_system.unified_search import UnifiedSearch

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


@app.post("/score/")
async def score(
    score_command: ScoreCommand,
    unified_search: UnifiedSearch = Depends(),
    email_reply_action: EmailReplyAction = Depends(),
):
    err_msg = ""
    result = None
    conversation = None
    session_id = score_command.conversation_id
    try:
        file_res = (
            await unified_search.adownload_file_from_minio(score_command.file_url) if score_command.file_url else None
        )
        print(file_res)
        result, conversation = await dialog_manager.handle_message(
            score_command.question, session_id, file_contents=[file_res] if file_res else None
        )
        if score_command.from_email and result and not isinstance(result, JumpOutResponse):
            result = await email_reply_action.run(ActionContext(conversation), result.answer)
    except Exception as err:
        logger.info(traceback.format_exc())
        err_msg = f"Error occurred: {err}"

    def generator():
        answer = "unknown error occurred"
        if result is None:
            if err_msg:
                answer = json.dumps({"answer": err_msg})
        elif isinstance(result, JumpOutResponse):
            answer = json.dumps({"answer": "Sorry, I can't help you with that."})
        else:
            answer = json.dumps(
                {
                    "answer": result.answer.get_content_with_extra_info(),
                    "session_id": session_id,
                    **(
                        dict(attachment=result.attachment.model_dump_json())
                        if isinstance(result, AttachmentResponse)
                        else {}
                    ),
                }
            )

        yield {"data": answer}
        full_history = []
        if conversation is not None:
            full_history = conversation.history.format_messages()
        PGModelLogService().log(
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


def main():
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
