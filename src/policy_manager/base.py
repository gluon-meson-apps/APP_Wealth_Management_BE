from typing import List

from action_runner.action import Action, ChitChatAction
from conversation_tracker.context import ConversationContext
from nlu.intent_with_entity import IntentWithEntity
from policy_manager.policy import Policy
from sdk.src.gluon_meson_sdk.models.chat_model import ChatModel


class PolicyManager:
    def get_action(self, intent: IntentWithEntity, conversation: ConversationContext, model_type: str) -> Action:
        pass


class BasePolicyManager(PolicyManager):
    def __init__(self, policies: List[Policy]):
        self.policies = policies

    # 如果有多个action，用一个大的action包装起来，还是视为一个action，用到组合模式
    def get_action(self, intent: IntentWithEntity, conversation: ConversationContext, model_type: str) -> Action:
        for policy in self.policies:
            handled, action = policy.handle(intent, conversation, model_type)
            if handled:
                return action
        return ChitChatAction(model_type, ChatModel(), conversation.current_enriched_user_input)
