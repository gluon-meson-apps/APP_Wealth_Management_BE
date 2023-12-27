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

    def construct_system_prompt(self, chat_history: list[dict[str, str]]):
        intent_list_str = json.dumps(
            [{'name': intent.name, 'description': intent.description} for intent in self.intent_list])

        chat_history_str = ""
        for chat in chat_history:
            i_or_you = "I" if chat["role"] == "user" else "You"
            chat_history_str += f"{i_or_you}: {chat['content']}\n"

        system_message = self.format_jinjia_template(self.template, intent_list=intent_list_str,
                                                     chat_history=chat_history_str)
        return system_message

    def format_message(self, role, content):
        return dict(role=role, content=content)

    def classify_intent(self, query: str, chat_history: list[dict[str, str]], examples) -> IntentClassificationResponse:
        system_message = self.construct_system_prompt(chat_history)
        history = [{"role": "system", "content": system_message}]
        logger.debug(examples)
        for example in examples:
            history.append(self.format_message("user", example["example"]))
            history.append(self.format_message("assistant", example["intent"]))
        history = history

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
