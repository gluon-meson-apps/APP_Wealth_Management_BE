import configparser

import requests
from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel

from utils.common import get_config_path


class IntentClassificationModelResponse(BaseModel):
    intent: str
    confidence: float


class IntentClassificationModel:
    def predict(self, text):
        return IntentClassificationModelResponse(intent="greet", confidence=0.9)


config = configparser.ConfigParser()
config.read(get_config_path())

MODEL_URL = config["JointBert"]["base_url"]


class JoinBertIntentClassificationModel(IntentClassificationModel):
    def __init__(self, model_url: str = MODEL_URL):
        self.model_url = model_url

    def predict(self, text):
        logger.info(f"user input is: {text}")
        payload = {"input_text": text}
        response = requests.post(self.model_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            name = data.get("intent_label")
            confidence = data.get("intent_confidence")
            return IntentClassificationModelResponse(intent=name, confidence=confidence)
        else:
            raise HTTPException(status_code=response.status_code, detail={response.text})
