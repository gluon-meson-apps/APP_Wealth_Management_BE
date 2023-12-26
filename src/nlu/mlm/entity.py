import configparser
import os
from typing import List

import requests
from fastapi import HTTPException
from loguru import logger

from nlu.base import EntityExtractor
from tracker.context import ConversationContext

from nlu.forms import FormStore
from nlu.intent_with_entity import Entity

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "../../", "config.ini"))

MODEL_URL = config["JointBert"]["base_url"]

BASE_SIG_VALUE = 0.5


class MLMEntityExtractor(EntityExtractor):
    def __init__(self, form_store: FormStore):
        self.form_store = form_store

    def extract_slots(self, utterance):
        # 提取槽位信息
        payload = {"input_text": utterance}
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

    def is_valid_entity(self, name, value, confidence, slot_dict):
        """
        检查实体是否有效
        """
        return (
            name in slot_dict
            and value is not None
            and confidence > BASE_SIG_VALUE
            and (isinstance(value, int) or len(value) > 0)
        )

    def extract_entity(self, conversation_context: ConversationContext) -> List[Entity]:
        # 获取实体和动作
        user_input = conversation_context.current_user_input
        intent = conversation_context.current_intent
        current_round = conversation_context.current_round

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
                (name, detail["value"], round(detail["confidence"], 2))
                for name, detail in entities.items()
                if self.is_valid_entity(
                    name, detail["value"], detail["confidence"], slot_dict
                )
            ]
        else:
            valid_entities = []

        def get_slot(name, value, confidence, priority):
            if slot_dict and name in slot_dict:
                return slot_dict[name].copy(
                    update={
                        "value": value,
                        "confidence": confidence,
                        "priority": priority,
                    }
                )
            return None

        # 创建实体列表和动作
        entity_list = [
            Entity(
                type=name,
                value=value,
                round=current_round,
                confidence=confidence,
                possible_slot=get_slot(name, value, confidence, current_round),
            )
            for name, value, confidence in valid_entities
        ]

        return entity_list
