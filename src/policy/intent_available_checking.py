from action.actions.intent_available_checking import IntentAvailableCheckingAction
from nlu.intent_with_entity import IntentWithEntity
from policy.base import Policy, PolicyResponse
from prompt_manager.base import PromptManager
from tracker.context import ConversationContext


class IntentAvailableCheckingPolicy(Policy):
    def __init__(self, prompt_manager: PromptManager):
        Policy.__init__(self, prompt_manager)

    def handle(self, IE: IntentWithEntity, context: ConversationContext) -> PolicyResponse:
        if IE.intent.disabled:
            return PolicyResponse(True, IntentAvailableCheckingAction())
        return PolicyResponse(False, None)
