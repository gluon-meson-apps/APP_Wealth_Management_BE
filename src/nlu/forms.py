from typing import List, Optional

from nlu.intent_with_entity import Slot, SlotType, Intent
from util import HashableBaseModel


# Form is the collection of slots
class Form(HashableBaseModel):
    name: str
    slots: List[Slot]

    def get_available_slots_str(self):
        return "、".join([f"{slot.name}[{slot.description}, 类型：{slot.slot_type}]" for slot in self.slots])


class FormStore:
    def __init__(self, intent_list_config):
        self.intent_list_config = intent_list_config

    def get_form_from_intent(self, intent: Intent) -> Optional[Form]:
        intent_config = self.intent_list_config.get_intent(intent.name)
        if intent_config is not None:
            return Form(name=intent_config.name,
                        slots=list(map(lambda slot: Slot.from_dict(slot_dict=slot), intent_config.slots)))
