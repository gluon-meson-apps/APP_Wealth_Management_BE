from action_runner.action import Action
from action_runner.context import ActionContext


class ActionRunner:
    def run(self, action: Action, context: ActionContext):
        raise NotImplementedError


class BaseActionRunner(ActionRunner):
    def run(self, action: Action, context: ActionContext):
        pass
