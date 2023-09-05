
from action_runner.action import Action  
from action_runner.context import ActionContext

class ActionRunner:

    def run(self, action: Action, context: ActionContext):
        raise NotImplementedError
        
class BaseActionRunner(ActionRunner):

    def __init__(self):
        self.actions = {}
        
    def register_action(self, name, action):
        self.actions[name] = action
        
    def run(self, action_name: str, context: ActionContext):
        if action_name not in self.actions:
            raise Exception(f"Action {action_name} not found")
            
        action = self.actions[action_name]
        action.run(context)