from typing import Any

from langchain.schema import Document
from loguru import logger
from pymilvus import FieldSchema, DataType

from gluon_meson_sdk.dbs.milvus.milvus_for_langchain import MilvusForLangchain
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.embedding_model import EmbeddingModel
from nlu.base import IntentClassifier
from nlu.intent_config import IntentListConfig
from nlu.intent_with_entity import Intent
from nlu.llm.intent_call import IntentCall
from prompt_manager.base import PromptManager
from third_system.search_entity import SearchResponse, SearchItem
from third_system.unified_search import UnifiedSearch
from tracker.context import ConversationContext

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
你是一个聊天机器人，你需要结合上下文对用户的意图进行识别，必须选择一个你认为最合适的意图，然后将其返回给我，不要返回多余的信息。

## 意图的可选项如下：
{intent_list}
"""

topic = "hsbc_topic_for_intent"


class IntentConfig:
    def __init__(self, name, examples, slots):
        self.name = name
        self.examples = examples
        self.slots = slots


def get_intent_examples(user_input: str) -> list[dict[str, Any]]:
    unified_search_client = UnifiedSearch()
    response: SearchResponse = unified_search_client.search_for_intent_examples(table=topic,
                                                                                user_input=user_input.strip())

    intents_examples = extract_examples_from_response_text(response)
    return intents_examples


def extract_examples_from_response_text(response: SearchResponse):
    intents_examples = []
    if response.total > 0:
        try:
            intent, example, score = extract_info(response.items)
            intents_examples.append({"example": example, "intent": intent, "score": score})
        except Exception as e:
            logger.warning(str(e))
    return intents_examples


def get_highest_scored_item(items: list[SearchItem]):
    sorted_items = sorted(items, key=lambda item: item.meta__score, reverse=True)
    return sorted_items[0]


def extract_info(items):
    highest_scored_item = get_highest_scored_item(items)
    text = highest_scored_item.model_extra["text"]
    intent = highest_scored_item.meta__reference.model_extra['meta__intent_result']
    example = text
    score = highest_scored_item.meta__score
    return intent, example, score


class LLMIntentClassifier(IntentClassifier):
    def __init__(
            self,
            chat_model: ChatModel,
            embedding_model: EmbeddingModel,
            milvus_for_langchain: MilvusForLangchain,
            intent_list_config: IntentListConfig,
            model_type: str,
            prompt_manager: PromptManager,
    ):
        self.model = chat_model
        self.embedding = embedding_model
        self.milvus_for_langchain = milvus_for_langchain
        self.retrieval_counts = 4
        self.embedding_type = "BASE_CH_P"
        self.model_type = model_type
        self.intent_list_config = intent_list_config
        self.prompt_manager = prompt_manager
        self.system_template_without_example = prompt_manager.load(
            name="intent_classification"
        )
        self.intent_call = IntentCall(
            intent_list_config.get_intent_list(),
            prompt_manager.load(name="intent_classification_v2").template,
            chat_model,
            model_type,
        )

    def train(self):
        # recreate topic
        # save all intent to milvus
        self.milvus_for_langchain.recreate_topic(
            topic,
            embedding_type=self.embedding_type,
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
                    metadata={"intent": intent, "source": "user upload"},
                )
                docs.append(doc)
        self.milvus_for_langchain.add_documents(
            topic, docs, embedding_type=self.embedding_type
        )

    def classify_intent(self, conversation: ConversationContext) -> Intent:
        user_input = conversation.current_user_input
        intent_name_list = self.intent_list_config.get_intent_name()
        chat_history = conversation.get_history().format_messages()
        intent_examples = get_intent_examples(user_input)
        intent = self.intent_call.classify_intent(user_input, chat_history, intent_examples)

        if intent.intent in intent_name_list:
            logger.info(f"session {conversation.session_id}, intent: {intent.intent}")
            description = self.intent_list_config.get_intent(intent.intent).description
            return Intent(name=intent.intent, confidence=intent.confidence, description=description)

        logger.info(f"intent: {intent.intent} is not predefined")
        return None
