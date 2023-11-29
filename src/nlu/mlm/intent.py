import os

import requests
import yaml
from fastapi import HTTPException
from loguru import logger

from conversation_tracker.context import ConversationContext
from nlu.intent_with_entity import Intent


class IntentConfig:
    def __init__(self, name, action, slots):
        self.name = name
        self.action = action
        self.slots = slots


class IntentListConfig:
    def __init__(self, intents):
        self.intents = intents

    def get_intent_list(self):
        # read resources/intent.yaml file and get intent list
        return [intent.name for intent in self.intents]

    def get_intent(self, intent_name):
        intents = [intent for intent in self.intents if intent.name == intent_name]
        return intents[0] if len(intents) > 0 else None

    def get_intent_and_examples(self):
        return [{'intent': intent_config.name, 'examples': intent_config.examples} for intent_config in self.intents]

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
                elif key == 'slots':
                    slots = data['slots']
                elif key == 'action':
                    action = data['action']

            intent = IntentConfig(name, action, slots)
            intents.append(intent)

        return cls(intents)


class IntentClassifier:
    def __init__(self):
        pass

    def get_intent(self, conversation: ConversationContext) -> Intent:
        url = "http://10.204.202.149:8000/predict/"
        payload = {"input_text": conversation.current_user_input}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            name = data.get("intent_label")
            confidence = data.get("intent_confidence")
            logger.info(f"name is {name}")
            logger.info(f"confidence is {confidence}")
            return Intent(name=name, confidence=confidence)
        else:
            raise HTTPException(
                status_code=response.status_code, detail={response.text}
            )
