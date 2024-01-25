from pydantic import BaseModel

from nlu.forms import FormStore
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext


class ActionContext:
    """Holds context information for executing actions."""

    def __init__(self, conversation: ConversationContext):
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
