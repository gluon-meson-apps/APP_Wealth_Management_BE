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
    def __init__(self, policies: List[Policy], action_model_type: str = None):
        self.policies = policies
        self.action_model_type = action_model_type

    # 如果有多个action，用一个大的action包装起来，还是视为一个action，用到组合模式
    def get_action(self, intent: IntentWithEntity, conversation: ConversationContext, model_type: str) -> Action:
        conversation.set_status('decision_making')
        model = self.action_model_type if self.action_model_type is not None else model_type
        if intent is not None:
            for policy in self.policies:
                handled, action = policy.handle(intent, conversation, model)
                if handled:
                    return action

        return ChitChatAction(model_type=model, chat_model=ChatModel(),
                              user_input=conversation.current_enriched_user_input)
