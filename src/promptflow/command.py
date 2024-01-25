from typing import Any, Union

from pydantic import BaseModel


class ScoreCommand(BaseModel):
    question: str
    conversation_id: str
    user_id: str
    file_url: Union[str, None] = None
    chat_history: Union[list[dict[str, Any]], None] = None
    from_email: Union[bool, None] = None
