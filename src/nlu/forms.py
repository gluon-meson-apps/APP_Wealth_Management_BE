from typing import List, Optional, Sequence

from nlu.intent_with_entity import Slot, Intent
from util import HashableBaseModel


class Form(HashableBaseModel):
    name: str
    slots: List[Slot]
    action: str
    slot_required: bool = False
    slot_expression: Optional[str] = None

    def has_slot_expression(self):
        return self.slot_expression is not None

    def get_slot_by_names(self, slot_names: Sequence[str]) -> list[Slot]:
        return [slot for slot in self.slots if slot.name in slot_names]

    def get_available_slots_str(self):
        return "\n".join(
            [
                f" * {slot.name}: {slot.description}, entity_type：{slot.slot_type}, entity_optional：{slot.optional}"
                for slot in self.slots
            ]
        )


class FormStore:
    def __init__(self, intent_list_config):
        self.intent_list_config = intent_list_config

    @staticmethod
    def _valid_slot(slot):
        return all(key in slot for key in ["name", "description", "slotType"])

    def _filter_and_process_slots(self, intent_slots):
        if intent_slots:
            filtered_slots = [slot for slot in intent_slots if self._valid_slot(slot)]
            slot_objects = [Slot.from_dict(slot) for slot in filtered_slots]
            slot_required = any(slot.get("required", False) for slot in intent_slots)
            return slot_objects, slot_required
        return [], False

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
            action=intent_config.action,
            slot_expression=intent_config.slot_expression,
        )
