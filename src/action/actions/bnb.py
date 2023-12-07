from pydantic import BaseModel
from gm_logger import get_logger
from action.base import Action

logger = get_logger()

class ActionResponse(BaseModel):
    text: str
    extra_info: dict = {}


class BankRelatedAction(Action):
    def __init__(self, action_name, possible_slots, intent):
        self.action_name = action_name
        self.possible_slots = possible_slots
        self.intent = intent

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action {self.action_name}')
        slots = [(slot.name, slot.value, slot.confidence) for slot in self.possible_slots]
        detail = {
            "slot": slots,
            "intent": self.intent
        }
        return ActionResponse(text=f"已为您完成{self.intent.description}", extra_info=detail)

class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        logger.info(f'exec action jump out')
        logger.debug("非范围内意图")
        return ActionResponse(text=f"Jump out")