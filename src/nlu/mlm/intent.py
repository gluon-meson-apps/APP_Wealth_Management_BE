import configparser

from loguru import logger

from caches.es import ElasticsearchCache
from models.intents.intent_classification import IntentClassificationModel
from nlu.base import IntentClassifier
from nlu.intent_config import IntentListConfig
from nlu.intent_with_entity import Intent
from tracker.context import ConversationContext
from utils.utils import get_config_path

config = configparser.ConfigParser()
config.read(get_config_path())

MODEL_URL = config["JointBert"]["base_url"]
use_cache = config.get("Cache", "enable").lower() == "true"


class MLMIntentClassifier(IntentClassifier):
    def __init__(
        self,
        intent_list_config: IntentListConfig,
        cache=ElasticsearchCache(),
        intent_model=IntentClassificationModel(),
        use_cache=use_cache,
    ):
        self.intent_list_config = intent_list_config
        self.cache = cache
        self.intent_model = intent_model
        self.use_cache = use_cache

    def classify_intent(self, conversation: ConversationContext) -> Intent:
        intent = None
        try:
            if self.use_cache:
                intent = self.get_from_cache(conversation)
        except Exception as e:
            logger.error(f"Failed to retrieve intent from cache: {e}")
        if not intent:
            intent = self.get_intent_without_cache(conversation)
        return intent

    def get_intent_without_cache(self, conversation: ConversationContext) -> Intent:
        intent = self.intent_model.predict(conversation.current_user_input)
        name = intent.intent
        confidence = intent.confidence
        intent = self.intent_list_config.get_intent(name)
        return Intent(
            name=name,
            confidence=confidence,
            description=intent.description if intent else "",
            business=intent.business,
            disabled=intent.disabled,
        )

    def get_from_cache(self, conversation):
        try:
            search_result = self.cache.search(conversation.current_user_input)
            logger.info(f"find intent from ES: {search_result}")
            if not search_result[1]:
                name = ""
            else:
                name = search_result[1][0]
            return Intent(name=name, confidence=1.0, description="")
        except Exception as e:
            logger.error(f"An error occurred while getting intent from ES: {str(e)}")
            raise e
