from typing import List, Dict, Any

from langchain.schema import Document
from pymilvus import FieldSchema, DataType

from gluon_meson_sdk.dbs.milvus.milvus_for_langchain import MilvusForLangchain
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.embedding_model import EmbeddingModel
from gm_logger import get_logger
from nlu.intent_with_entity import Intent
from nlu.llm.context import FullLlmConversationContext

logger = get_logger()

# should extract to a config file
system_template = """
你是一个聊天机器人，你需要对用户的意图进行识别，必须选择一个你认为最合适的意图，然后将其返回给我，不要返回多余的信息。

## 意图的可选项如下：
{intent_list}

## 下面是一些示例：
{examples}

## 问题：
消息：{question}
意图：
"""

system_template_without_example = """
你是一个聊天机器人，你需要对用户的意图进行识别，必须选择一个你认为最合适的意图，然后将其返回给我，不要返回多余的信息。

## 意图的可选项如下：
{intent_list}
"""

topic = "test_topic_for_intent"

import yaml

class IntentConfig:
    def __init__(self, name, examples, slots):
        self.name = name
        self.examples = examples
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
        return [ {'intent': intent_config.name, 'examples': intent_config.examples} for intent_config in self.intents]

    @classmethod
    def from_yaml_file(cls, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        intents = []
        for intent_details in data['intents']:
            intent_name, examples, slots = None, None, None
            for key in intent_details:
                if 'examples' == key:
                    examples = intent_details['examples']
                elif 'intent' == key:
                    intent_name = intent_details['intent']
                elif 'slots' == key:
                    slots = intent_details['slots']
            intent = IntentConfig(intent_name, examples, slots)
            intents.append(intent)

        return cls(intents)

class IntentClassifier:
    def __init__(self,
                    chat_model: ChatModel,
                    embedding_model: EmbeddingModel,
                    milvus_for_langchain: MilvusForLangchain,
                    intent_list_config,
                    model_type: str,):
        self.model = chat_model
        self.embedding = embedding_model
        self.milvus_for_langchain = milvus_for_langchain
        self.retrieval_counts = 4
        self.embedding_type = "E5"
        self.model_type = model_type
        self.intent_list_config = intent_list_config

    def train(self):
        # recreate topic
        # save all intent to milvus
        self.milvus_for_langchain.recreate_topic(
            topic, embedding_type=self.embedding_type,
            extra_meta_fields=[FieldSchema("intent", DataType.VARCHAR, max_length=256)],
            max_length=1024,
        )
        intent_examples = self.intent_list_config.get_intent_and_examples()
        docs = []
        for intent_example in intent_examples:
            intent = intent_example["intent"]
            examples = intent_example["examples"]
            for example in examples:
                doc = Document(
                    page_content=example,
                    metadata={'intent': intent, 'source': 'user upload'}
                )
                docs.append(doc)
        self.milvus_for_langchain.add_documents(topic, docs, embedding_type=self.embedding_type)



    def get_intent_examples(self, user_input: str) -> list[dict[str, Any]]:
        search_with_score = self.milvus_for_langchain.query_docs(topic, user_input, embedding_type=self.embedding_type,
                                                                 k=self.retrieval_counts)
        intents = []
        for result in search_with_score:
            example = result[0].page_content
            intent = result[0].metadata['intent']
            score = result[1]
            intents.append({
                "example": example,
                "intent": intent,
                "score": score
            })
        return intents

    def format_examples(self, examples: List[Dict[str, Any]]) -> str:
        template = """消息：{question}
意图：{intent}
"""
        return "\n".join([template.format(question=example["example"], intent=example["intent"]) for example in examples])

    def classify_intent_using_llm(self, intent_list: List[str], examples: List[Dict[str, Any]], question: str) -> str:
        intent_list_str = "\n".join([f"- {intent}" for intent in intent_list])
        examples_str = self.format_examples(examples)
        system_message = system_template.format(intent_list=intent_list_str, examples=examples_str, question=question)
        logger.debug(system_message)
        intent = self.model.chat_single(system_message, model_type=self.model_type, max_length=1024)
        return intent

    def classify_intent_using_llm_with_few_shot_history(self, intent_list: List[str], examples: List[Dict[str, Any]], question: str) -> str:
        intent_list_str = "\n".join([f"- {intent}" for intent in intent_list])
        system_message = system_template_without_example.format(intent_list=intent_list_str)
        history = [('system', system_message)]
        user_template = """消息：{question}
意图："""
        for example in examples:
            history.append(('user', user_template.format(question=example['example'])))
            history.append(('assistant', example['intent']))

        intent = self.model.chat_single(user_template.format(question=question), history=history, model_type=self.model_type, max_length=1024)
        logger.debug(question)
        logger.debug(history)
        return intent.response


    def classify_intent(self, conversation_context: FullLlmConversationContext) -> Intent:
        user_input = conversation_context.get_current_user_input()
        intent_list = self.intent_list_config.get_intent_list()
        question = user_input
        intent_examples = self.get_intent_examples(user_input)

        intent = self.classify_intent_using_llm_with_few_shot_history(intent_list, intent_examples, question)
        # TODO: Check whether the intent matches the intent list
        return Intent(name=intent, confidence=1.0)
