import gm_logger
from conversation_tracker.context import ConversationContext
from nlu.base import Nlu
from nlu.intent_with_entity import IntentWithEntity
from nlu.llm.context import FullLlmConversationContext
from nlu.llm.entity import EntityExtractor
from nlu.llm.intent import IntentClassifier

logger = gm_logger.get_logger()

class LLMNlu(Nlu):
    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor

    def extract_intents_and_entities(self, conversation: ConversationContext) -> IntentWithEntity:
        llm_conversation_context = FullLlmConversationContext(conversation)

        conversation.set_status('intent_classifying')
        current_intent = self.intent_classifier.classify_intent(llm_conversation_context)
        if current_intent is not None:
            llm_conversation_context.conversation_context.current_intent = current_intent
            conversation.set_status('slot_filling')
            current_entities = self.entity_extractor.extract_entity(llm_conversation_context)
            logger.info("entities: %s", str(list(map(lambda entity: (entity.type, entity.value), current_entities))))
            return IntentWithEntity(intent=current_intent, entities=current_entities)
        else:
            return None
