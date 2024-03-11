from loguru import logger
from tracker.context import ConversationContext
from nlu.base import Nlu, IntentClassifier, EntityExtractor
from nlu.intent_with_entity import IntentWithEntity, Intent


def should_use_latest_history(
    current_intent: Intent, start_new_question: bool, previous_intent_name: str, is_providing_more_info: bool
) -> bool:
    if current_intent.ignore_previous_slots:
        if start_new_question:
            return True
        return previous_intent_name != current_intent.get_full_intent_name() or not is_providing_more_info
    return False


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

        previous_intent_name = conversation.current_intent.get_full_intent_name() if conversation.current_intent else ""
        current_intent = await self.intent_classifier.classify_intent(conversation)

        if current_intent is None:
            logger.info("No intent found")
            return IntentWithEntity(intent=None, entities=[], action="")

        is_providing_more_info = False
        if not conversation.start_new_question:
            is_providing_more_info = await self.intent_classifier.check_is_providing_more_info(conversation)

        use_latest_history = should_use_latest_history(
            current_intent, conversation.start_new_question, previous_intent_name, is_providing_more_info
        )
        if use_latest_history:
            conversation.history.keep_latest_n_rounds(1)

        if conversation.is_confused_with_intents():
            return IntentWithEntity(intent=current_intent, entities=[], action="")

        conversation.handle_intent(current_intent)
        logger.info(f"Current intent: {conversation.current_intent}")
        logger.info(f"Start new question: {conversation.start_new_question}")

        logger.info("extracting utterance's slots")
        current_entities = await self.entity_extractor.extract_entity(conversation)
        # Retain entities
        # If the user start a new topic and the current intent is set to ignore previous slots, then the existing entities will be ignored
        existing_entities = [] if use_latest_history else conversation.get_entities()
        merged_entities = self.merge_entities(
            existing_entities, current_entities, conversation.get_current_intent_slot_names()
        )

        entities_string = str([(entity.type, entity.value, entity.confidence) for entity in merged_entities])
        conversation.add_entity(current_entities)
        logger.info(f"Session {conversation.session_id}, entities: {entities_string}")

        return IntentWithEntity(intent=conversation.current_intent, entities=merged_entities, action="")
