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
    def __init__(self, name, description, action, slots):
        self.name = name
        self.description = description
        self.action = action
        self.slots = slots


class IntentListConfig:
    def __init__(self, intents):
        self.intents = intents
        self._initialize_fixed_intents()

    def _initialize_fixed_intents(self):
        # Initialize fixed intents like chitchat, slot_filling
        chitchat = IntentConfig("chitchat", "闲聊", "chitchat", [])
        slot_filling = IntentConfig("slot_filling", "追问槽位", "slot_filling", [])
        positive = IntentConfig("positive", "肯定", "positive", [])
        negative = IntentConfig("negative", "否认", "negative", [])

        self.intents.extend([chitchat, slot_filling, positive, negative])

    def get_intent_list(self):
        # read resources/intent.yaml file and get intent list
        return [intent.description for intent in self.intents]

    def get_intent(self, intent_name):
        intents = [intent for intent in self.intents if intent.name == intent_name]
        return intents[0] if len(intents) > 0 else None

    def get_intent_and_attrs(self):
        return [
            {'intent': intent_config.name, 'examples': intent_config.examples, 'description': intent_config.description}
            for intent_config in self.intents]

    @classmethod
    def from_scenes(cls, folder_path):
        intents = []
        files = [f for f in os.listdir(folder_path) if f.endswith('.yaml')]

        for file_name in files:
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)

            name, action, slots = None, None, None
            for key in data:
                if key == 'name':
                    name = data['name']
                elif key == 'description':
                    description = data['description']
                elif key == 'slots':
                    slots = data['slots']
                elif key == 'action':
                    action = data['action']

            intent = IntentConfig(name, description, action, slots)
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
            return Intent(name=name, confidence=confidence, description=intent.description if intent else "")
        else:
            raise HTTPException(
                status_code=response.status_code, detail={response.text}
            )

    @staticmethod
    def get_intent_from_es(conversation):
        elasticsearch_manager = ElasticsearchManager()
        try:
            search_result = elasticsearch_manager.search_by_question(question=conversation.current_user_input)
            logger.info(f"find intent from ES: {search_result[1]}")
            return Intent(name=','.join(search_result[1]), confidence=1.0, description="")
        except Exception as e:
            logger.error(f"An error occurred while getting intent from ES: {str(e)}")
            raise e

    def handle_intent(self, context: ConversationContext, next_intent: Intent) -> ConversationContext:

        # if slot_filling intent found, we will not change current intent to next intent
        if next_intent.name not in ["slot_filling", "negative", "positive"]:
            context.update_intent(next_intent)

        # if no obviously intent found before, throw out to fusion engine
        if context.current_intent is None and next_intent.name in ["slot_filling", "positive", "negative"]:
            context.update_intent(None)

        # if last round set conversation state "intent_confirm" and user confirmed in current round
        if next_intent.name in ["positive"] and context.state in ["intent_confirm"]:
            context.current_intent.confidence = 1.0
            
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


