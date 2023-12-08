import configparser
from loguru import logger
from tracker.context import ConversationContext
from nlu.base import Nlu
from nlu.intent_with_entity import IntentWithEntity
from nlu.mlm.entity import EntityExtractor
from nlu.mlm.intent import IntentClassifier

config = configparser.ConfigParser()
config.read('config.ini')

class IntegratedNLU(Nlu):
    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor

    def merge_entities(self, existing_entities, current_entities):
        merged_entities = {entity.possible_slot.name if entity.possible_slot else None: entity for entity in existing_entities}

        for entity in current_entities:
            if entity.possible_slot and entity.possible_slot.name:
                merged_entities[entity.possible_slot.name] = entity

        return list(merged_entities.values())

    def extract_intents_and_entities(self, conversation: ConversationContext) -> IntentWithEntity:
        conversation.set_status("analyzing user's intent")

        current_intent = None
        use_elasticsearch = config.get('elasticsearch', 'enable').lower() == 'true'
        
        try:
            if use_elasticsearch:
                current_intent = self.intent_classifier.get_intent_from_es(conversation)
        except Exception as e:
            logger.error(f"Failed to retrieve intent from Elasticsearch: {e}")

        if not current_intent:
            current_intent = self.intent_classifier.get_intent_from_model(conversation)

        conversation = self.intent_classifier.handle_intent(conversation, current_intent)
        logger.info(f"Current intent: {conversation.current_intent}")

        logger.info("extracting utterance's slots")
        current_entities, action = self.entity_extractor.get_entity_and_action(conversation)
        # Retain entities
        existing_entities = conversation.get_entities()
        merged_entities = self.merge_entities(existing_entities, current_entities)

        entities_string = str([(entity.type, entity.value, entity.confidence) for entity in merged_entities])
        conversation.add_entity(current_entities)
        logger.info(f"Session {conversation.session_id}, entities: {entities_string}")

        return IntentWithEntity(intent=conversation.current_intent, entities=merged_entities, action=action)