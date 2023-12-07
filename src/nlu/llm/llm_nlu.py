from loguru import logger
from tracker.context import ConversationContext
from nlu.base import Nlu
from nlu.intent_with_entity import IntentWithEntity
from nlu.llm.entity import EntityExtractor
from nlu.llm.intent import IntentClassifier

class LLMNlu(Nlu):
    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor

    def extract_intents_and_entities(self, conversation: ConversationContext) -> IntentWithEntity:

        conversation.set_status('intent_classifying')
        current_intent = self.intent_classifier.classify_intent(conversation)
        if current_intent is not None:
            conversation.current_intent = current_intent
            conversation.set_status('slot_filling')
            current_entities = self.entity_extractor.extract_entity(conversation)
            entities_string = str(list(map(lambda entity: (entity.type, entity.value), current_entities)))
            logger.info("user %s, entities: %s", conversation.session_id, entities_string)
            return IntentWithEntity(intent=current_intent, entities=current_entities)
        else:
            return None
