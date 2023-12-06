import uuid
from datetime import datetime
from typing import List, Any

from gm_logger import get_logger
from nlu.intent_with_entity import Entity, Intent

logger = get_logger()

class History:
    def __init__(self, histories: List[dict[str, Any]], max_history: int = 4):
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
        self.intent_queue: List[Intent] = [] 
        self.current_enriched_user_input = None
        self.history = History([])
        # used for logging
        self.status = 'start'
        
        # used for condition jughment
        self.state = None
        self.entities: List[Entity] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        # counter for inquiry times
        self.inquiry_times = 0

    def get_history(self) -> History:
        return self.history

    def append_history(self, role: str, message: str):
        self.history.add_history(role, message)
        
    def add_entity(self, entities: List[Entity]):
        self.entities += entities
    
    def update_entity(self, updated_entity: Entity) -> bool:
        for index, entity in enumerate(self.entities):
            if entity.name == updated_entity.name:
                self.entities[index] = updated_entity
                logger.info("Updated slot %s for session %s", updated_entity.name, self.session_id)
                return True  # Slot updated successfully
        return False  # Slot with given name not found

    def get_entities(self) -> List[Entity]:
        return self.entities
    
    def flush_entities(self):
        self.entities = []

    def set_status(self, status: str):
        self.status = status
        logger.info("session %s, conversation status: %s", self.session_id, status)
        
    def set_state(self, state: str):
        self.state = state
        
    def update_intent(self, intent: Intent):
        self.current_intent = intent
        self.intent_queue.append(intent)