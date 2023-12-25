from action.base import DynamicAction, ActionResponse
from action.context import ActionConfigContext
from action.repository.action_repository import ActionRepository


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

