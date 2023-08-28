from conversation_tracker.base import ConversationTracker
from nlu.intent_with_entity import IntentWithEntity


class Nlu:
    def extract_intents_and_entities(self, conversation_tracker: ConversationTracker) -> str:
        raise NotImplementedError()


class BaseNlu(Nlu):
    def extract_intents_and_entities(self, conversation_tracker: ConversationTracker) -> IntentWithEntity:
        pass
