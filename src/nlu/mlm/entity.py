from typing import List

import requests
from fastapi import HTTPException
from loguru import logger

from conversation_tracker.context import ConversationContext

from nlu.forms import FormStore
from nlu.intent_with_entity import Entity

class EntityExtractor:
    def __init__(self, form_store: FormStore):
        self.form_store = form_store
    
    def extract_slots(self, utterance):
        url = "http://10.204.202.149:8000/predict/"
        payload = {'input_text': utterance}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            slots: dict[str, str] = data.get("slot_labels")
            logger.info(f"slots is {slots}")
            return slots
        else:
            raise HTTPException(
                status_code=response.status_code, detail={response.text}
            )

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