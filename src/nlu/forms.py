from typing import List, Optional


from util import HashableBaseModel
from nlu.intent_with_entity import Slot, SlotType, Intent


# Form is the collection of slots
class Form(HashableBaseModel):
    name: str
    slots: List[Slot]

    def get_available_slots_str(self):
        return "、".join([f"{slot.name}[{slot.description}, 类型：{slot.slot_type}]" for slot in self.slots])


class FormStore:
    def __init__(self):
        pass
    
    def get_form_from_intent(self, intent: Intent) -> Optional[Form]:
        if intent.name == "控制智能家居":
            return Form(name="控制智能家居", slots=[
                Slot(name="位置", description="智能家居所处的房间", slot_type=SlotType.TEXT),
                Slot(name="操作", description="对智能家居进行的操作", slot_type=SlotType.TEXT),
                Slot(name="对象", description="哪一种智能家居", slot_type=SlotType.NUMERIC),
                Slot(name="操作值", description="操作的时候，需要考虑的参数，比如灯是开启还是关闭，灯的亮度需要调到多少", slot_type=SlotType.NUMERIC_OR_TEXT),
            ])
        if intent.name == "页面字体缩放":
            return Form(name="页面字体缩放", slots=[
                Slot(name="缩放值", description="放大多少或者缩小多少", slot_type=SlotType.NUMERIC),
                Slot(name="操作", description="放大或者缩小", slot_type=SlotType.TEXT)]
                        )
