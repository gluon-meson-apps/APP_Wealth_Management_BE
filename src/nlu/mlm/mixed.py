import gm_logger
from conversation_tracker.context import ConversationContext
from nlu.base import Nlu
from nlu.intent_with_entity import IntentWithEntity
from nlu.mlm.entity import EntityExtractor
from nlu.mlm.intent import IntentClassifier

logger = gm_logger.get_logger()

class MixedNLU(Nlu):
    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor

    def extract_intents_and_entities(self, conversation: ConversationContext) -> IntentWithEntity:

        conversation.set_status("analyzing user's intent")
        current_intent = self.intent_classifier.get_intent(conversation)
        if current_intent is not None:
            conversation.current_intent = current_intent
            conversation.set_status("extracting utterance's slots")
            current_entities, action = self.entity_extractor.get_entity_and_action(conversation)
            entities_string = str(list(map(lambda entity: (entity.type, entity.value), current_entities)))
            logger.info("user %s, entities: %s", conversation.user_id, entities_string)
            
            print(action)
            return IntentWithEntity(intent=current_intent, entities=current_entities, action=action)
        else:
            return None
