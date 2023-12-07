import uuid
from datetime import datetime
from typing import Dict, List, Any

from gm_logger import get_logger
from nlu.intent_with_entity import Entity, Intent
from collections import deque

logger = get_logger()

class History:
    def __init__(self, histories: List[dict[str, Any]], max_history: int = 6):
        self.max_history = max_history
        self.histories = histories[-self.max_history:]

    def add_history(self, role: str, message: str):
        if len(self.histories) >= self.max_history:
            self.histories.pop(0)
        self.histories.append({'role': role, 'content': message})

    def format_to_string(self):
        return '\n'.join([f'{entry["role"]}: {entry["content"]}' for entry in self.histories])


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
        self.state = None
        self.entities = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        # counter for inquiry times
        self.inquiry_times = 0
        self.has_update = False

    def get_history(self) -> History:
        return self.history

    def append_history(self, role: str, message: str):
        self.history.add_history(role, message)
        
    def add_entity(self, entities: List[Entity]):
        self.has_update = True
        entity_map: Dict[str, Entity] = {entity.type: entity for entity in self.entities}
        
        for new_entity in entities:
            if new_entity.type in entity_map:
                existing_entity = entity_map[new_entity.type]
                existing_entity.value = new_entity.value
                existing_entity.role = new_entity.role
                existing_entity.confidence = new_entity.confidence
                existing_entity.possible_slot = new_entity.possible_slot
                logger.info("Updated entity %s for session %s", new_entity.type, self.session_id)
            else:
                self.entities.append(new_entity)
                logger.info("Added entity %s for session %s", new_entity.type, self.session_id)

    def get_entities(self):
        return self.entities
    
    def flush_entities(self):
        self.entities = []

    def set_status(self, status: str):
        self.status = status
        logger.info("session %s, conversation status: %s", self.session_id, status)
        
    def set_state(self, state: str):
        self.state = state
        keywords = ["filling", "confirm"]
        if any(keyword in state for keyword in keywords):
            self.inquiry_times += 1
        
    def update_intent(self, intent: Intent):
        self.current_intent = intent
        if intent is not None:
            self.intent_queue.append(intent)
            if intent.name != self.current_intent.name:
                self.inquiry_times = 0