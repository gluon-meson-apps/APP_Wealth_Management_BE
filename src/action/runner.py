from action.base import Action
from action.context import ActionContext


class ActionRunner:
    """Interface for action runner."""

    def run(self, action: Action, context: ActionContext):
        """Run the given action with the provided context."""
        raise NotImplementedError

    def register_actions(self, action: Action):
        """Register an action."""
        raise NotImplementedError


class SimpleActionRunner(ActionRunner):
    def run(self, action: Action, context: ActionContext):
        return action.run(context)


class BaseActionRunner(ActionRunner):
    """Basic implementation of an action runner."""

    def __init__(self):
        """Initialize the action runner, storing registered actions."""
        self.actions = {}

    def register_actions(self, name, action):
        """
        Register an action by name.

        Args:
            name: Name to register action under.
            action: Action instance to register.
        """
        self.actions[name] = action

    async def run(self, action_name: str, context: ActionContext):
        """
        Run registered action by name.

        Args:
            action_name: Name of registered action.
            context: Action context.

        Raises:
            Exception: If action name not found.
        """
        if action_name not in self.actions:
            raise Exception(f"Action {action_name} not found")

        action = self.actions[action_name]
        result = await action.run(context)
        return result
