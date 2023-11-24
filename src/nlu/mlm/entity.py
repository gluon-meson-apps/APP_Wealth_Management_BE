from typing import List

from conversation_tracker.context import ConversationContext
from gm_logger import get_logger
from nlu.intent_with_entity import Entity
from nlu.forms import FormStore

logger = get_logger()

class EntityExtractor:
    def __init__(self, form_store: FormStore):
        self.form_store = form_store
    
    def extract_slots(self, utterance):
        return {'账号': "1234"}

    def get_entity_and_action(self, conversation_context: ConversationContext) -> List[Entity]:
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent)

        if not form:
            logger.debug(f"The intent [{intent.name}] does not require entity extraction")
            return []

        entities = self.extract_slots(user_input)
        slot_dict = {slot.name: slot for slot in form.slots}

        if entities:
            valid_entities = [(name, value) for name, value in entities.items() if name in slot_dict
                            and value is not None and (isinstance(value, int) or len(value) > 0)]
        else:
            valid_entities = []

        def get_slot(name, value):
            if slot_dict and name in slot_dict:
                return slot_dict[name].copy(update={'value': value})
            return None

        return [
            Entity(type=name, value=value, possible_slot=get_slot(name, value))
            for name, value in valid_entities
        ], form.action