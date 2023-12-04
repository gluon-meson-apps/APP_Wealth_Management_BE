import os
from urllib.request import Request

from dotenv import load_dotenv
from starlette.responses import JSONResponse

from dialog_manager.base import BaseDialogManager, DialogManagerFactory
from fastapi import FastAPI
from uvicorn import run
from pydantic import BaseModel

load_dotenv()

app = FastAPI()


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as err:
        err_msg = f"Error occurred: {err}"
        print(err_msg)
        return JSONResponse(status_code=500, content=err_msg)


class MessageInput(BaseModel):
    session_id: str
    user_input: str


dialog_manager: BaseDialogManager = DialogManagerFactory.create_dialog_manager()


@app.post("/chat/")
def chat(data: MessageInput):
    session_id = data.session_id
    user_input = data.user_input
    result, conversation = dialog_manager.handle_message(user_input, session_id)
    return {"response": result, "conversation": conversation}


def main():
    if os.getenv("LOCAL_MODE") == '1':
        run("app:app", host="0.0.0.0", port=7788, reload=True,
            reload_dirs=os.path.dirname(os.path.abspath(__file__)))
    else:
        run("app:app", host="0.0.0.0", port=7788)


if __name__ == "__main__":
    main()
