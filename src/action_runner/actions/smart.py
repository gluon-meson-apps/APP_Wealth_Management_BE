import gm_logger
from action_runner.action import Action, ActionResponse

logger = gm_logger.get_logger()


class SmartHomeOperatingAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:smart_home_operating')
        logger.debug("成功控制了智能家居")
        return ActionResponse(text=self.response)
    