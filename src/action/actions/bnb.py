from pydantic import BaseModel
from gm_logger import get_logger
from action.base import Action

logger = get_logger()

class ActionResponse(BaseModel):
    text: str
    extra_info: dict = {}


class BankRelatedAction(Action):
    def __init__(self, action_name, possible_slots):
        self.action_name = action_name
        self.possible_slots = possible_slots

    def run(self, context) -> ActionResponse:
        context.set_status(f'action: {self.action_name}')
        slots = [(slot.name, slot.value) for slot in self.possible_slots]
        return ActionResponse(text=f"已为您完成{self.action_name}, slots: {slots}")


class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        context.set_status('action:jump out')
        logger.debug("非范围内意图")
        return ActionResponse(text=f"Jump out")