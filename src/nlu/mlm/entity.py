import configparser
import os
from typing import List, Any

import requests
from fastapi import HTTPException
from loguru import logger

# from common.constant import MODEL_URL
from tracker.context import ConversationContext

from nlu.forms import FormStore
from nlu.intent_with_entity import Entity

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../../', 'config.ini'))

MODEL_URL = config['JointBert']['base_url']

BASE_SIG_VALUE = 0.8

class EntityExtractor:
    def __init__(self, form_store: FormStore):
        self.form_store = form_store

    def extract_slots(self, utterance):
        # 提取槽位信息
        payload = {'input_text': utterance}
        response = requests.post(MODEL_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            slots = data.get("slot_labels")
            logger.info(f"Slots: {slots}")
            return slots
        else:
            raise HTTPException(
                status_code=response.status_code, detail={response.text}
            )

    def is_valid_entity(self, name, value, slot_dict):
        """
        检查实体是否有效
        """
        return (
            name in slot_dict
            and value is not None
            and (
                isinstance(value, int)
                or (isinstance(value, dict) and len(value) > 0)
            )
        )

    def get_entity_and_action(self, conversation_context: ConversationContext) -> (List[Entity], str):
        # 获取实体和动作
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        form = self.form_store.get_form_from_intent(intent) if intent else None

        if not form:
            if not intent:
                logger.debug(f"No intent found for user_input: {user_input}")
            else:
                logger.debug(f"The intent [{intent.name}] does not require entities")
            return [], ""

        entities = self.extract_slots(user_input)
        slot_dict = {slot.name: slot for slot in form.slots}

        if entities:
            valid_entities = [
                (name, value)
                for name, value in entities.items()
                if self.is_valid_entity(name, value, slot_dict)
            ]
        else:
            valid_entities = []

        def get_slot(name, value):
            if slot_dict and name in slot_dict:
                return slot_dict[name].copy(update={'value': value["value"]})
            return None

        # 创建实体列表和动作
        entity_list = [
            Entity(type=name, value=value["value"], confidence=value["confidence"], possible_slot=get_slot(name, value))
            for name, value in valid_entities if value["confidence"] > BASE_SIG_VALUE
        ]
        action = form.action

        return entity_list, action
