import configparser
import os

import requests
import yaml
from fastapi import HTTPException
from loguru import logger

from caches.es import ElasticsearchCache
from models.intents.intent_classification import IntentClassificationModel
from nlu.base import IntentClassifier
from tracker.context import ConversationContext
from nlu.intent_with_entity import Intent

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../../', 'config.ini'))

MODEL_URL = config['JointBert']['base_url']
use_cache = config.get('Cache', 'enable').lower() == 'true'


class IntentConfig:
    def __init__(self, name, description, business, action, slots):
        self.name = name
        self.description = description
        self.action = action
        self.slots = slots
        self.business = business


class IntentListConfig:
    def __init__(self, intents):
        self.intents = intents
        self._initialize_fixed_intents()

    def _initialize_fixed_intents(self):
        fixed_intents = [
            ("slot_filling", "追问槽位", False, "slot_filling", []),
            ("positive", "肯定", False, "positive", []),
            ("negative", "否认", False, "negative", [])
        ]

        for intent_data in fixed_intents:
            name, description, business, action, slots = intent_data
            intent = IntentConfig(name, description, business, action, slots)
            self.intents.append(intent)

    def get_intent_list(self):
        return self.intents

    def get_intent(self, intent_name):
        return next((intent for intent in self.intents if intent.name == intent_name), None)

    def get_intent_and_attrs(self):
        return [
            {'intent': intent.name, 'examples': intent.examples, 'description': intent.description}
            for intent in self.intents
        ]

    @classmethod
    def from_scenes(cls, folder_path):
        intents = []
        files = [f for f in os.listdir(folder_path) if f.endswith('.yaml')]

        for file_name in files:
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)

            intent = IntentConfig(
                name=data.get('name'),
                description=data.get('description'),
                business=data.get('business'),
                action=data.get('action'),
                slots=data.get('slots')
            )
            intents.append(intent)

        return cls(intents)


class MLMIntentClassifier(IntentClassifier):
    def __init__(self, intent_list_config: IntentListConfig, cache=ElasticsearchCache(),
                 intent_model=IntentClassificationModel(), use_cache=use_cache):
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
        return Intent(name=name, confidence=confidence, description=intent.description if intent else "",
                      business=intent.business)

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