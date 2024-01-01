import configparser
import os
import traceback
from typing import Optional
from urllib.request import Request


from sse_starlette import EventSourceResponse
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, Form, Depends
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from uvicorn import run

from action.base import ErrorResponse
from dialog_manager.base import BaseDialogManager, DialogManagerFactory
from promptflow.command import ScoreCommand
from router import api_router

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
def chat(
    score_command: ScoreCommand
):
    result, conversation = dialog_manager.handle_message(score_command.question, score_command.id, [])
    def generator():
        yield {"data": {"answer": result.answer, "session_id": conversation.session_id}}
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
