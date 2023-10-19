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
from nlu.llm.intent import IntentClassifier
from nlu.llm.llm_nlu import LLMNlu
from output_adapter.base import BaseOutputAdapter
from policy_manager.base import BasePolicyManager
from policy_manager.policy import SlotCheckPolicy, SmartHomeOperatingPolicy

if __name__ == '__main__':
    import os
    # construct BaseDialogManager
    # call handle_message
    pwd = os.path.dirname(os.path.abspath(__file__))
    intent_config_file_path = os.path.join(pwd, '.', 'resources', 'intent.yaml')
    model_type = "azure_gpt35"

    embedding_model = EmbeddingModel()
    classifier = IntentClassifier(chat_model=ChatModel(), embedding_model=embedding_model,
                                  milvus_for_langchain=MilvusForLangchain(embedding_model, MilvusConnection()),
                                  intent_config_path=intent_config_file_path,
                                  model_type=model_type)
    form_store = FormStore()

    entity_extractor = EntityExtractor(form_store, ChatModel(), model_type=model_type)

    policy_manager = BasePolicyManager([SlotCheckPolicy(form_store), SmartHomeOperatingPolicy()])

    result = BaseDialogManager(BaseConversationTracker(), BaseInputEnricher(),
                               LLMNlu(classifier, entity_extractor), policy_manager, SimpleActionRunner(),
                               BaseOutputAdapter(), model_type=model_type).handle_message("帮忙打开卧室的空调", "123")
    print(result)

    # How embedding model works?
    # How to configure OpenAI API Key
    # How to connect to gluon-meson api endpoint
    #
