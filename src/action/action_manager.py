from action.base import DynamicAction, ActionResponse, Action
from action.context import ActionConfigContext
from action.repository.action_repository import ActionRepository


class ActionManager:
    def __init__(self, action_repository: ActionRepository, action_config_context: ActionConfigContext):
        self.action_repository = action_repository
        self.action_config_context = action_config_context

    def add_action(self, action: Action):
        self.action_repository.save(action)

    def add_dynamic_action(self, action_code: str, class_name: str):
        the_globals = {
            "DynamicAction": DynamicAction,
            "ActionResponse": ActionResponse,
            "ActionConfigContext": ActionConfigContext,
            "action_config_context": self.action_config_context,
            '__builtins__': {
                '__build_class__': __build_class__,
                '__name__': __name__,
                'str': str,
            }
        }
        the_locals = {}
        exec(action_code +f"\nreturned_action={class_name}()\nreturned_action.load_from_config_context(action_config_context)", the_globals, the_locals)
        action: DynamicAction = the_locals['returned_action']
        self.action_repository.save(action)
