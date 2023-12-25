from action.base import DynamicAction, ActionResponse
from action.context import ActionConfigContext
from action.repository.action_repository import ActionRepository, MemoryBasedActionRepository


class ActionManager:
    def __init__(self, action_repository: ActionRepository, action_config_context: ActionConfigContext):
        self.action_repository = action_repository
        self.action_config_context = action_config_context

    def add_dynamic_action(self, action_code: str):
        globals = {
            "DynamicAction": DynamicAction,
            "ActionResponse": ActionResponse,
            "ActionConfigContext": ActionConfigContext,
            "__builtins__": __builtins__,
        }
        exec(action_code, globals)
        action: DynamicAction = globals['returned_action']
        self.action_repository.save(action)


if __name__ == '__main__':
    dynamic_action_code = """
class TestAction(DynamicAction):
    def get_name(self) -> str:
        return "test_action"
        
    def run(self, context) -> ActionResponse:
        return ActionResponse(code=200, message="success", answer={}, jump_out_flag=False)
        
    def load_from_config_context(self, config_context: ActionConfigContext):
        pass
    

returned_action=TestAction()
"""
    action_manager = ActionManager(MemoryBasedActionRepository(), None)
    action_manager.add_dynamic_action(dynamic_action_code)
