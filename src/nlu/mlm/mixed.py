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
        
    def merge_entities(self, existed_entities, current_entities):
        merged_entities = {entity.possible_slot.name if entity.possible_slot else None: entity for entity in existed_entities}

        for entity in current_entities:
            if entity.possible_slot and entity.possible_slot.name:
                merged_entities[entity.possible_slot.name] = entity

        return list(merged_entities.values())

    def extract_intents_and_entities(self, conversation: ConversationContext) -> IntentWithEntity:

        conversation.set_status("analyzing user's intent")
        current_intent = self.intent_classifier.get_intent(conversation)
        
        # intent changed
        if current_intent is not None:
            conversation.current_intent = current_intent

        conversation.set_status("extracting utterance's slots")
        current_entities, action = self.entity_extractor.get_entity_and_action(conversation)
        entities_string = str(list(map(lambda entity: (entity.type, entity.value), current_entities)))
        logger.info("user %s, entities: %s", conversation.session_id, entities_string)
        
        # keep entities
        existed_entities = conversation.get_entities()
        merged_entities = self.merge_entities(existed_entities, current_entities)

        entities_string = str(list(map(lambda entity: (entity.type, entity.value), merged_entities)))
        conversation.add_entity(current_entities)
        
        logger.info("user %s, entities: %s", conversation.session_id, entities_string)
        
        return IntentWithEntity(intent=current_intent, entities=merged_entities, action=action)
