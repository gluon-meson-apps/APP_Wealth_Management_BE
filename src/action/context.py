from pydantic import BaseModel

from nlu.forms import FormStore
from prompt_manager.base import PromptManager


class ActionContext:
    """Holds context information for executing actions."""

    def __init__(self, conversation):
        """Initialize empty context."""
        self.conversation = conversation

    def set_status(self, status):
        """Set the status of the conversation."""
        self.conversation.set_status(status)


class ActionConfigContext(BaseModel):
    prompt_manager: PromptManager
    form_store: FormStore

    class Config:
        arbitrary_types_allowed = True
