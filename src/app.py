import os
from urllib.request import Request

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from uvicorn import run

from dialog_manager.base import BaseDialogManager, DialogManagerFactory

load_dotenv()

app = FastAPI()
dialog_manager: BaseDialogManager = DialogManagerFactory.create_dialog_manager()


class ErrorResponse(BaseModel):
    code: int
    message: str
    answer: dict = {}
    jump_out_flag: bool


if os.getenv("LOCAL_MODE") == '1':
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
        print(err_msg)
        return JSONResponse(status_code=500,
                            content=ErrorResponse(
                                code=500, message=err_msg, answer={}, jump_out_flag=True).__dict__)


class MessageInput(BaseModel):
    session_id: str
    user_input: str


@app.post("/chat/")
def chat(data: MessageInput):
    session_id = data.session_id
    user_input = data.user_input
    result, conversation = dialog_manager.handle_message(user_input, session_id)
    return {"response": result, "conversation": conversation, "session_id": conversation.session_id}


@app.get("/healthy/")
async def healthcheck():
    return {"status": "alive"}


def main():
    if os.getenv("LOCAL_MODE") == '1':
        run("app:app", host="0.0.0.0", port=7788, reload=True,
            reload_dirs=os.path.dirname(os.path.abspath(__file__)))
    else:
        run("app:app", host="0.0.0.0", port=7788)


if __name__ == "__main__":
    # session_id = "123"
    # user_input = "天气好"
    # result, conversation = dialog_manager.handle_message(user_input, session_id)
    main()
