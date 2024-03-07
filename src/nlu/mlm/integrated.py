from loguru import logger
from tracker.context import ConversationContext
from nlu.base import Nlu, IntentClassifier, EntityExtractor
from nlu.intent_with_entity import IntentWithEntity


class IntegratedNLU(Nlu):
    def __init__(self, intent_classifier: IntentClassifier, entity_extractor: EntityExtractor):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor

    def merge_entities(self, existing_entities, current_entities, current_intent_slot_names):
        merged_entities = {
            entity.type if entity else None: entity
            for entity in existing_entities
            if current_intent_slot_names and entity.type in current_intent_slot_names
        }

        for entity in current_entities:
            merged_entities[entity.type] = entity

        return list(merged_entities.values())

    async def extract_intents_and_entities(self, conversation: ConversationContext) -> IntentWithEntity:
        conversation.set_status("analyzing user's intent")

        current_intent, start_new_topic = await self.intent_classifier.classify_intent(conversation)
        if current_intent and conversation.is_confused_with_intents():
            return IntentWithEntity(intent=current_intent, entities=[], action="")

        if current_intent is None:
            logger.info("No intent found")
            return IntentWithEntity(intent=None, entities=[], action="")

        conversation.handle_intent(current_intent)
        logger.info(f"Current intent: {conversation.current_intent}")

        logger.info("extracting utterance's slots")
        current_entities = await self.entity_extractor.extract_entity(conversation)
        # Retain entities
        # If the user start a new topic and the current intent is set to ignore previous slots, then the existing entities will be ignored
        existing_entities = (
            [] if start_new_topic and conversation.current_intent.ignore_previous_slots else conversation.get_entities()
        )
        merged_entities = self.merge_entities(
            existing_entities, current_entities, conversation.get_current_intent_slot_names()
        )

        entities_string = str([(entity.type, entity.value, entity.confidence) for entity in merged_entities])
        conversation.add_entity(current_entities)
        logger.info(f"Session {conversation.session_id}, entities: {entities_string}")

        return IntentWithEntity(intent=conversation.current_intent, entities=merged_entities, action="")
