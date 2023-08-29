from typing import List, Optional

from pydantic import BaseModel

from nlu.intent_with_entity import Slot, SlotType


class Form(BaseModel):
    name: str
    slots: List[Slot]

    def get_available_slots_str(self):
        return "、".join([f"{slot.name}[{slot.description}, 类型：{slot.slot_type}]" for slot in self.slots])

class FormStore:
    def __init__(self):
        pass

    def get_form_from_intent(self, intent):
        return Form(name="页面字体缩放", slots=[
            Slot(name="缩放值", description="放大多少或者缩小多少", slot_type=SlotType.numeric),
            Slot(name="操作", description="放大或者缩小", slot_type=SlotType.TEXT)]
        )
