from typing import List, Optional

from nlu.intent_with_entity import Slot, Intent
from util import HashableBaseModel

class Form(HashableBaseModel):
    name: str
    slots: List[Slot]
    slot_required: bool = False
    action: str

    def get_available_slots_str(self):
        return "\n".join(
            [
                f" * {slot.name}: {slot.description}, 类型：{slot.slot_type}, 是否可选：{slot.optional}"
                for slot in self.slots
            ]
        )

class FormStore:
    def __init__(self, intent_list_config):
        self.intent_list_config = intent_list_config

    @staticmethod
    def _valid_slot(slot):
        return all(key in slot for key in ['name', 'description', 'slotType', 'optional'])

    def _filter_and_process_slots(self, intent_slots):
        filtered_slots = [slot for slot in intent_slots if self._valid_slot(slot)]
        slot_objects = [Slot.from_dict(slot) for slot in filtered_slots]
        slot_required = any(slot.get('required', False) for slot in intent_slots)
        return slot_objects, slot_required

    def get_form_from_intent(self, intent: Intent) -> Optional[Form]:
        if not intent:
            return None
        
        intent_config = self.intent_list_config.get_intent(intent.name)
        if intent_config is None:
            return None

        slots, slot_required = self._filter_and_process_slots(intent_config.slots)
        
        return Form(
            name=intent_config.name,
            slots=slots,
            slot_required=slot_required,
            action=intent_config.action
        )