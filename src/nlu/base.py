from typing import List

from conversation_tracker.context import ConversationContext
from nlu.intent_with_entity import IntentWithEntity


class Nlu:
    def extract_intents_and_entities(self, conversation_tracker: ConversationContext) -> IntentWithEntity:
        raise NotImplementedError()


class BaseNlu(Nlu):
    def extract_intents_and_entities(self, conversation_tracker: ConversationContext) -> IntentWithEntity:
        pass


