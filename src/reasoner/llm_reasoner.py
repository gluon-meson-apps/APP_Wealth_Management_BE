from action.base import Action
from nlu.base import Nlu
from policy.base import PolicyManager
from reasoner.base import Plan, Reasoner
from tracker.context import ConversationContext


class LlmReasoner(Reasoner):
    def __init__(self, nlu: Nlu, policy_manager: PolicyManager, model_type: str):
        self.policy_manager = policy_manager
        self.nlu = nlu
        self.model_type = model_type

    def greet(self, conversation_context: ConversationContext) -> Action:
        return self.policy_manager.get_greet_action(conversation_context, self.model_type)

    async def think(self, conversation: ConversationContext) -> Plan:
        conversation.set_status("reasoning")
        intent_with_entities = await self.nlu.extract_intents_and_entities(conversation)
        action = self.policy_manager.get_action(intent_with_entities, conversation, self.model_type)

        return Plan(intent_with_entities, "", action, [])
