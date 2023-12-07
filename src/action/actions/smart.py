from loguru import logger
from src.action.base import Action, ActionResponse


class SmartHomeOperatingAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:smart_home_operating')
        logger.debug("成功控制了智能家居")
        return ActionResponse(text=self.response)
    