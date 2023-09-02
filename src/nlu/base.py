from conversation_tracker.base import ConversationTracker
from conversation_tracker.context import ConversationContext
from nlu.full_llm.context import FullLlmConversationContext
from nlu.full_llm.entity import EntityExtractor
from nlu.full_llm.intent import IntentClassifier
from nlu.intent_with_entity import IntentWithEntity


class Nlu:
    def extract_intents_and_entities(self, conversation_tracker: ConversationTracker) -> str:
        raise NotImplementedError()


class BaseNlu(Nlu):
    def extract_intents_and_entities(self, conversation_tracker: ConversationTracker) -> IntentWithEntity:
        pass


class FullLLMNlu(Nlu):
    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor

    def extract_intents_and_entities(self, conversation_context: ConversationContext) -> IntentWithEntity:
        llm_conversation_context = FullLlmConversationContext(conversation_context)
        current_intent = self.intent_classifier.classify_intent(llm_conversation_context)

        llm_conversation_context.conversation_context.current_intent = current_intent

        current_entities = self.entity_extractor.extract_entity(llm_conversation_context)
        return IntentWithEntity(intent=current_intent, entities=current_entities)
