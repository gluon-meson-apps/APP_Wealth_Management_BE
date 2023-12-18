import uuid
from datetime import datetime
from typing import List, Any

from action.base import ResponseMessageType
from nlu.intent_with_entity import Entity, Intent
from collections import deque

from loguru import logger


class History:
    def __init__(self, rounds: List[dict[str, Any]], max_history: int = 6):
        self.max_history = max_history
        self.rounds = rounds[-self.max_history:]

    def add_history(self, role: str, message: str):
        if len(self.rounds) >= self.max_history:
            self.rounds.pop(0)
        self.rounds.append({'role': role, 'content': message})

    def format_string(self):
        return '\n'.join([f'{entry["role"]}: {entry["content"]}' for entry in self.rounds])


class ConversationContext:
    def __init__(self, current_user_input: str, session_id: str, current_user_intent: Intent = None):
        self.current_user_input = current_user_input
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.current_intent = current_user_intent
        self.intent_queue = deque(maxlen=3)
        self.history = History([])
        # used for logging
        self.status = 'start'
        # used for condition jughment
        self.state = ""
        self.entities = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        # counter for inquiry times
        self.inquiry_times = 0
        self.has_update = False
        self.current_round = 0

    def get_history(self) -> History:
        return self.history

    def append_user_history(self, message: str):
        self.history.add_history("user", message)

    def append_assistant_history(self, answer):
        response_content = self._prepare_response_content(answer)
        self.history.add_history("assistant", response_content)

    def _prepare_response_content(self, answer):
        if not answer:
            return "Jump out"
        elif answer.messageType == ResponseMessageType.FORMAT_TEXT:
            return answer.content
        elif answer.messageType == ResponseMessageType.FORMAT_INTELLIGENT_EXEC:
            return f"已为您完成 {answer.content.businessInfo['instruction']}"
        else:
            return ""

    def add_entity(self, entities: List[Entity]):
        entity_map = {entity.type: entity for entity in self.entities}

        for new_entity in entities:
            if new_entity.type in entity_map:
                self.has_update = True
                existing_entity = entity_map[new_entity.type]
                existing_entity.__dict__.update(new_entity.__dict__)
                logger.info(f"Updated entity {new_entity.type} for session {self.session_id}")
            else:
                self.entities.append(new_entity)
                logger.info(f"Added entity {new_entity.type} for session {self.session_id}")

    def get_entities(self):
        return self.entities

    def flush_entities(self):
        self.entities = []

    def set_status(self, status: str):
        self.status = status
        logger.info(f"session {self.session_id}, conversation status: {status}")

    def set_state(self, state: str):
        self.state = state
        keywords = ["intent_filling", "intent_confirm"]
        if any(keyword in state for keyword in keywords):
            self.inquiry_times += 1

    def update_intent(self, intent: Intent):
        if intent is not None:
            self.has_update = True
            self.intent_queue.append(intent)
            if intent != self.current_intent:
                self.inquiry_times = 0
        self.current_intent = intent

    def intent_restore(self):
        self.current_intent = self.intent_queue[0]
