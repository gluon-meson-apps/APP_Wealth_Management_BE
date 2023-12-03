import os

import requests
import yaml
from fastapi import HTTPException
from loguru import logger

from common.constant import MODEL_URL
from conversation_tracker.context import ConversationContext
from nlu.intent_with_entity import Intent


class IntentConfig:
    def __init__(self, name, description, action, slots):
        self.name = name
        self.description = description
        self.action = action
        self.slots = slots


class IntentListConfig:
    def __init__(self, intents):
        self.intents = intents

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

    def get_intent(self, conversation: ConversationContext) -> Intent:
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

    def handle_intent(self, context: ConversationContext, next_intent: Intent) -> ConversationContext:
        
        # if slot_filling intent found, we will not change current intent
        if next_intent.name not in ["slot_filling", "negative", "positive"]:
            context.current_intent = next_intent

        # if no obviously intent found before, set current intent as [skill_irrelevant]
        if context.current_intent is None and next_intent.name in ["slot_filling"]:
            context.current_intent = next_intent
            context.current_intent.name = 'skill_irrelevant'
        
        # if conversation
        if next_intent.name in ["positive"] and context.state in ["intent_confirm"]:
            context.current_intent.confidence = 1.0
            
        if next_intent.name in ["negative"] and context.state in ["intent_confirm"]:
            context.current_intent.confidence = 0.0

        return context
