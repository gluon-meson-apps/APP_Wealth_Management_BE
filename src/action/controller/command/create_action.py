from pydantic import BaseModel


class CreateActionCommand(BaseModel):
    class_name: str
    action_code: str
