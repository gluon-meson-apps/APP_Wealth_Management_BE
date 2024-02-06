from typing import List, Optional

from tracker.context import ConversationContext
from nlu.intent_with_entity import IntentWithEntity, Entity, Intent


class Nlu:
    def extract_intents_and_entities(self, conversation_context: ConversationContext) -> IntentWithEntity:
        raise NotImplementedError()


class BaseNlu(Nlu):
    def extract_intents_and_entities(self, conversation_context: ConversationContext) -> IntentWithEntity:
        pass


class EntityExtractor:
    def extract_entity(self, conversation_context: ConversationContext) -> List[Entity]:
        raise NotImplementedError()


class IntentClassifier:
    def classify_intent(self, conversation_context: ConversationContext) -> tuple[Optional[Intent], Optional[Intent]]:
        raise NotImplementedError()
