from typing import Any, Optional

from pydantic import BaseModel


class ScoreCommand(BaseModel):
    question: str
    id: str
    chat_history: Optional[list[dict[str, Any]]]