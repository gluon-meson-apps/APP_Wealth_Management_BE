from abc import ABC, abstractmethod
from pydantic import BaseModel

from action.context import ActionContext
from loguru import logger

class ActionResponse(BaseModel):
    text: str
    extra_info: dict = {}


class Action(ABC):
    """Base abstract class for all actions."""

    @abstractmethod
    def run(self, context: ActionContext) -> ActionResponse:
        """Run the action given the context."""
        pass