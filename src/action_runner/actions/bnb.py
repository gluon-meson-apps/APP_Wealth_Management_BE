from pydantic import BaseModel
from gm_logger import get_logger
from action_runner.action import Action

logger = get_logger()

class ActionResponse(BaseModel):
    text: str
    extra_info: dict = {}


class BankRelatedAction(Action):
    def __init__(self, action_name):
        self.action_name = action_name

    def run(self, context) -> ActionResponse:
        context.set_status(f'action: {self.action_name}')
        # logger.debug(f"intent:{context.intent}, slots: {}")
        return ActionResponse(text=f"bank related action {self.action_name} triggered")
    
class JumpOut(Action):
    def __init__(self):
        pass

    def run(self, context) -> ActionResponse:
        context.set_status('action:jump out')
        logger.debug("非范围内意图")
        return ActionResponse(text=self.response)