import configparser
import os

import requests
import yaml
from fastapi import HTTPException
from loguru import logger

from elastic_search_manager.base import ElasticsearchManager
from tracker.context import ConversationContext
from nlu.intent_with_entity import Intent

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../../', 'config.ini'))

MODEL_URL = config['JointBert']['base_url']


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

class IntentClassifier:
    def __init__(self, intent_list_config: IntentListConfig):
        self.intent_list_config = intent_list_config

    def get_intent_from_model(self, conversation: ConversationContext) -> Intent:
        logger.info(f"user input is: {conversation.current_user_input}")
        payload = {"input_text": conversation.current_user_input}
        response = requests.post(MODEL_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            name = data.get("intent_label")
            confidence = data.get("intent_confidence")
            intent = self.intent_list_config.get_intent(name)
            logger.info(f"find intent {name} with confidence {confidence}")
            return Intent(name=name, confidence=confidence, description=intent.description if intent else "", business=intent.business)
        else:
            raise HTTPException(
                status_code=response.status_code, detail={response.text}
            )

    @staticmethod
    def get_intent_from_es(conversation):
        elasticsearch_manager = ElasticsearchManager()
        try:
            search_result = elasticsearch_manager.search_by_question(question=conversation.current_user_input)
            logger.info(f"find intent from ES: {search_result}")
            if not search_result[1]:
                name=""
            else:
                name = search_result[1][0]
            return Intent(name=name, confidence=1.0, description="")
        except Exception as e:
            logger.error(f"An error occurred while getting intent from ES: {str(e)}")
            raise e

    def handle_intent(self, context: ConversationContext, next_intent: Intent) -> ConversationContext:
        
        # if intent same as last round, no need to update
        if context.current_intent and next_intent.name == context.current_intent.name:
            return context

        # if slot_filling intent found, we will not change current intent to next intent
        if next_intent.name not in ["slot_filling", "negative", "positive"]:
            context.update_intent(next_intent)

        # if no obviously intent found before, throw out to fusion engine
        if context.current_intent is None and next_intent.name in ["slot_filling", "positive", "negative"]:
            context.update_intent(None)

        # if last round set conversation state "intent_confirm" and user confirmed in current round
        if next_intent.name in ["positive"] and context.state in ["intent_confirm"]:
            context.current_intent.confidence = 1.0
        
        # if last round set conversation state "slot_confirm" and user confirmed in current round
        if next_intent.name in ["positive"] and context.state.startswith('slot_confirm'):
            slot_name = context.state.split(':')[1].strip()
            for entity in context.entities:
                if entity.type == slot_name:
                    entity.confidence = 1.0
                    entity.possible_slot.confidence = 1.0
                    break

        # if user deny in current round
        if next_intent.name in ["negative"]:
            context.update_intent(None)

        return context