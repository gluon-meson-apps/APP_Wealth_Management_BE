from datetime import datetime
from typing import List, Any

from gm_logger import get_logger
from nlu.intent_with_entity import Entity, Intent

logger = get_logger()

class History:
    def __init__(self, histories: List[dict[str, Any]]):
        self.histories = histories

    def add_history(self, role: str, message: str):
        self.histories.append({'role': role, 'content': message})

    def format_to_string(self):
        return '\n'.join([f'{entry["role"]}: {entry["content"]}' for entry in self.histories])


class ConversationContext:
    def __init__(self, current_user_input: str, session_id: str, current_user_intent: Intent = None):
        self.current_user_input = current_user_input
        self.session_id = session_id
        self.current_intent = current_user_intent
        self.current_enriched_user_input = None
        self.history = History([])
        self.status = 'start'
        self.entities: List[Entity] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

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
                logger.info("Updated slot %s for user %s", updated_entity.name, self.session_id)
                return True  # Slot updated successfully
        return False  # Slot with given name not found

    def get_entities(self) -> List[Entity]:
        return self.entities
    
    def flush_entities(self):
        self.entities = []

    def set_status(self, status: str):
        self.status = status
        logger.info("user %s, conversation status: %s", self.session_id, status)