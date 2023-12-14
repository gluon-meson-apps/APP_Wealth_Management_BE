from typing import List, Tuple

from action.actions.general import EndDialogueAction
from action.base import Action

from tracker.context import ConversationContext
from nlu.intent_with_entity import IntentWithEntity
from prompt_manager.base import PromptManager


class Policy:

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    def handle(self, intent: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        return NotImplementedError

    @staticmethod
    def get_possible_slots(intent: IntentWithEntity):
        return {entity.possible_slot for entity in intent.entities if Policy.is_not_empty(entity)}

    @staticmethod
    def is_not_empty(entity):
        return entity.value is not None and entity.value != ''


class PolicyManager:
    def get_greet_action(self, conversation: ConversationContext, model_type: str) -> Action:
        pass

    def get_action(self, intent: IntentWithEntity, conversation: ConversationContext, model_type: str) -> Action:
        pass


class BasePolicyManager(PolicyManager):
    def __init__(self, policies: List[Policy], prompt_manager: PromptManager, action_model_type: str = None):
        self.policies = policies
        self.prompt_manager = prompt_manager
        self.action_model_type = action_model_type

    def get_action(self, intent: IntentWithEntity, conversation: ConversationContext, model_type: str) -> Action:
        conversation.set_status('decision_making')
        if intent is not None:
            for policy in self.policies:
                handled, action = policy.handle(intent, conversation)
                if handled:
                    return action
                
        return EndDialogueAction()
