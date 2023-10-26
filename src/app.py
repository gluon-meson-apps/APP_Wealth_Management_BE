import os

from action_runner.base import SimpleActionRunner
from conversation_tracker.base import BaseConversationTracker
from dialog_manager.base import BaseDialogManager
from gluon_meson_sdk.dbs.milvus.milvus_connection import MilvusConnection
from gluon_meson_sdk.dbs.milvus.milvus_for_langchain import MilvusForLangchain
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.embedding_model import EmbeddingModel
from input_enricher.base import BaseInputEnricher
from nlu.forms import FormStore
from nlu.llm.entity import EntityExtractor
from nlu.llm.intent import IntentClassifier, IntentListConfig
from output_adapter.base import BaseOutputAdapter
from policy_manager.base import BasePolicyManager
from policy_manager.policy import SlotCheckPolicy, SmartHomeOperatingPolicy, RAGPolicy
from reasoner.llm_reasoner import LlmReasoner


def create_reasoner(model_type, action_model_type):
    embedding_model = EmbeddingModel()
    intent_list_config = IntentListConfig.from_yaml_file(intent_config_file_path)
    classifier = IntentClassifier(chat_model=ChatModel(), embedding_model=embedding_model,
                                  milvus_for_langchain=MilvusForLangchain(embedding_model, MilvusConnection()),
                                  intent_list_config=intent_list_config,
                                  model_type=model_type)
    form_store = FormStore(intent_list_config)
    entity_extractor = EntityExtractor(form_store, ChatModel(), model_type=model_type)
    policy_manager = BasePolicyManager(policies=[SlotCheckPolicy(form_store), SmartHomeOperatingPolicy(), RAGPolicy()],
                                       action_model_type=action_model_type)
    return LlmReasoner(classifier, entity_extractor, policy_manager, model_type)


if __name__ == '__main__':

    pwd = os.path.dirname(os.path.abspath(__file__))
    intent_config_file_path = os.path.join(pwd, '.', 'resources', 'intent.yaml')
    model_type = "azure_gpt35"
    action_model_type = 'gpt-4'

    reasoner = create_reasoner(model_type, action_model_type)
    base_dialog_manager = BaseDialogManager(BaseConversationTracker(), BaseInputEnricher(),
                                            reasoner, SimpleActionRunner(), BaseOutputAdapter())

    user_input = input("You: ")
    while user_input != "stop":
        # 打开卧室的空调
        # 温度26度制冷
        result = base_dialog_manager.handle_message(user_input, "123")
        print(result)
        user_input = input("You: ")
