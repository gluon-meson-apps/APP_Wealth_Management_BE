from typing import List

from action.base import Action
from tracker.context import ConversationContext
from nlu.intent_with_entity import IntentWithEntity


class Plan:
    intent: IntentWithEntity
    content: str
    action: Action
    parameters: List[object]

    def __init__(
        self,
        intent: IntentWithEntity,
        content: str,
        action: Action,
        parameters: List[object],
    ):
        self.intent = intent
        self.content = content
        self.action = action
        self.parameters = parameters


class Reasoner:
    async def think(self, conversation_tracker: ConversationContext) -> Plan:
        raise NotImplementedError()

    def greet(self, conversation_tracker: ConversationContext) -> Action:
        raise NotImplementedError()
