from typing import Any, Union

from pydantic import BaseModel


class ScoreCommand(BaseModel):
    question: str
    id: str
    file_url: Union[str, None] = None
    chat_history: Union[list[dict[str, Any]], None] = None
