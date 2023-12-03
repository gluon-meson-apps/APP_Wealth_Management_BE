from pydantic import BaseModel
from gm_logger import get_logger
from action.action import Action

logger = get_logger()

class ActionResponse(BaseModel):
    text: str
    extra_info: dict = {}


class PrintStatementAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:print_statement')
        logger.debug("成功查询打印了回单")
        return ActionResponse(text=self.response)
    
class FontPageAdjustmentAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:font_page_adjustment')
        logger.debug("成功调整了页面字体")
        return ActionResponse(text=self.response)
    
class AdjustTableColumnAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:adjust_table_column')
        logger.debug("成功调整了表头")
        return ActionResponse(text=self.response)
    
class ActivateFunctionAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:activate_function')
        logger.debug("成功开通了功能")
        return ActionResponse(text=self.response)
    
class QAAction(Action):
    def __init__(self, response):
        self.response = response

    def run(self, context) -> ActionResponse:
        context.set_status('action:qa')
        logger.debug("成功跳转到小招X")
        return ActionResponse(text=self.response)