from typing import List, Any

from gm_logger import get_logger
from nlu.intent_with_entity import Intent

logger = get_logger()

class History:
    def __init__(self, histories: List[dict[str, Any]]):
        self.histories = histories

    def add_history(self, role: str, message: str):
        self.histories.append({'role': role, 'content': message})

    def format_to_string(self):
        return '\n'.join([f'{entry["role"]}: {entry["content"]}' for entry in self.histories])


class ConversationContext:
    def __init__(self, current_user_input: str, user_id: str, current_user_intent: Intent = None):
        self.current_user_input = current_user_input
        self.user_id = user_id
        self.current_intent = current_user_intent
        self.current_enriched_user_input = None
        self.history = History([])
        self.status = 'start'

    def get_history(self) -> History:
        return self.history

    def append_history(self, role: str, message: str):
        self.history.add_history(role, message)

    def set_status(self, status: str):
        self.status = status
        logger.info("user %s: , conversation status: %s", self.user_id, status)