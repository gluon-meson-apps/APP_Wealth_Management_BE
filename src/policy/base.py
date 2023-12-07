from typing import List, Tuple

from llm.self_host import ChatModel

from action.actions.general import ChitChatAction
from action.base import Action

from tracker.context import ConversationContext
from nlu.intent_with_entity import IntentWithEntity
from prompt_manager.base import PromptManager


class Policy:

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    def handle(self, intent: IntentWithEntity, context: ConversationContext) -> Tuple[bool, Action]:
        pass

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

    # 如果有多个action，用一个大的action包装起来，还是视为一个action，用到组合模式
    def get_action(self, intent: IntentWithEntity, conversation: ConversationContext, model_type: str) -> Action:
        conversation.set_status('decision_making')
        model = self.action_model_type if self.action_model_type is not None else model_type
        if intent is not None:
            for policy in self.policies:
                handled, action = policy.handle(intent, conversation)
                if handled:
                    return action
                
        return ChitChatAction(model_type=model, chat_model=ChatModel(), user_input=conversation.current_enriched_user_input)
