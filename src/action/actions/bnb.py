import configparser
from enum import unique, Enum

from loguru import logger
from pydantic import BaseModel

from action.base import Action
from output_adapter.base import OutputAdapter

config = configparser.ConfigParser()
config.read('config.ini')


class ActionResponse(BaseModel):
    code: int
    message: str
    answer: dict = {}
    jump_out_flag: bool


@unique
class ActionType(str, Enum):
    activate_function = "activate_function"
    page_reduce = "page_reduce"
    page_enlarge = "page_enlarge"
    page_resize = "page_resize"
    add_header = "add_header"
    remove_header = "remove_header"


operateTypeDict = {
    "activate_function": "ACTIVATE_FUNCTION",
    "page_reduce": "PAGE_RESIZE_INCREMENT",
    "page_enlarge": "PAGE_RESIZE_INCREMENT",
    "page_resize": "PAGE_RESIZE_TARGET",
    "add_header": "ADJUST_HEADER",
    "remove_header": "ADJUST_HEADER",
}

actionSlotsTypeDict = {
    "activate_function": ["functions"],
    "page_reduce": ["font_decrease", "font_size"],
    "page_enlarge": ["font_increase", "font_size"],
    "page_resize": ["font_size"],
    "add_header": ["header_element"],
    "remove_header": ["header_element", "header_position"],
}

operateSlotCategoryTypeDict = {
    "page_reduce": "DECREASE",
    "page_enlarge": "INCREASE",
    "add_header": "ADD",
    "remove_header": "REMOVE",
}

operateSlotValueTypeDict = {
    "header_element": "NAME",
    "header_position": "INDEX",
}


class BankRelatedAction(Action):
    def __init__(self, action_name, possible_slots, intent, output_adapter: OutputAdapter):
        self.action_name = action_name
        self.possible_slots = possible_slots
        self.intent = intent
        self.output_adapter = output_adapter

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action {self.action_name}')
        target_slots = [x for x in self.possible_slots if x.name in actionSlotsTypeDict[self.action_name]]
        if len(target_slots) > 1:
            target_slots.sort(key=lambda x: x.priority, reverse=True)
        target_slot_value = self.output_adapter.normalize_slot_value(
            target_slots[0].value if len(target_slots) > 0 else config.get('defaultActionSlotValue',
                                                                           self.action_name))
        target_slot_name = self.output_adapter.normalize_slot_value(
            target_slots[0].name if len(target_slots) > 0 else actionSlotsTypeDict[self.action_name][0])
        slot = dict()
        if self.action_name == ActionType.activate_function or self.action_name == ActionType.page_resize:
            slot = {
                "value": target_slot_value
            }
        elif self.action_name == ActionType.page_reduce or self.action_name == ActionType.page_enlarge:
            slot = {
                "category": operateSlotCategoryTypeDict[self.action_name],
                "value": target_slot_value
            }

        elif self.action_name == ActionType.add_header or self.action_name == ActionType.remove_header:
            slot = {
                "category": operateSlotCategoryTypeDict[self.action_name],
                "valueType": operateSlotValueTypeDict[target_slot_name],
                "value": target_slot_value
            }

        detail = {
            "messageType": "FORMAT_INTELLIGENT_EXEC",
            "content": {
                "businessId": "N35010Operate",
                "operateType": operateTypeDict[self.action_name],
                "operateSlots": slot,
                "businessInfo": {}
            },
        }

        return ActionResponse(code=200, message="success", answer=detail, jump_out_flag=False)


class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        logger.debug("非范围内意图")
        return ActionResponse(code=200, message="success", answer=dict(), jump_out_flag=True)
