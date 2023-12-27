from pydantic import BaseModel


class CreateActionResponse(BaseModel):
    class_name: str
    action_code: str
