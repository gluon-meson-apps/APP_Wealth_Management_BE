import json
from typing import List, Dict, Any

from jinja2 import Environment
from loguru import logger
from pydantic import BaseModel

from llm.self_host import ChatModel
from nlu.intent_config import IntentConfig


class IntentClassificationResponse(BaseModel):
    intent: str
    confidence: float


class IntentCall:
    def __init__(self,
                 intent_list: List[IntentConfig],
                 template: str,
                 model: ChatModel,
                 model_type: str,
                 ):
        self.model = model
        self.model_type = model_type
        self.intent_list = intent_list
        self.template = template


    def format_jinjia_template(self, template: str, **kwargs) -> str:
        template = Environment().from_string(template)
        return template.render(**kwargs)

    def construct_system_prompt(self, chat_history):
        intent_list_str = json.dumps([{'name': intent.name, 'description': intent.description} for intent in self.intent_list])

        system_message = self.format_jinjia_template(self.template, intent_list=intent_list_str)
        return system_message

    def classify_intent(self, query: str, chat_history, examples) -> IntentClassificationResponse:
        system_message = self.construct_system_prompt(chat_history)
        history = [("system", system_message)]
        user_template = """消息：{question}
意图："""
        # for example in examples:
        #     history.append(("user", user_template.format(question=example["example"])))
        #     history.append(("assistant", example["intent"]))

        intent = self.model.chat(
            query,
            history=history,
            model_type=self.model_type,
            max_length=1024,
        )
        logger.debug(query)
        logger.debug(history)
        logger.debug(system_message)
        logger.debug(intent)
        response = IntentClassificationResponse.parse_obj(json.loads(intent))
        
        return response
