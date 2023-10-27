from gluon_meson_sdk.dbs.milvus.milvus_connection import MilvusConnection
from gluon_meson_sdk.dbs.milvus.milvus_for_langchain import MilvusForLangchain
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.embedding_model import EmbeddingModel
from nlu.llm.intent import IntentClassifier, IntentListConfig
import argparse


def add_intent_examples(intent_yaml):
    import os
    pwd = os.path.dirname(os.path.abspath(__file__))
    intent_config_file_path = os.path.join(pwd, '../../', 'resources', intent_yaml)
    intent_list_config = IntentListConfig.from_yaml_file(intent_config_file_path)
    embedding_model = EmbeddingModel()
    classifier = IntentClassifier(chat_model=ChatModel(), embedding_model=embedding_model,
                                  milvus_for_langchain=MilvusForLangchain(embedding_model, MilvusConnection()),
                                  intent_list_config=intent_list_config,
                                  model_type="azure_gpt35")
    classifier.train()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='thought agent tools')
    parser.add_argument('--add-intent-examples',
                        help='add intents as examples for intent classifier')

    args = parser.parse_args()
    if args.add_intent_examples:
        add_intent_examples(args.add_intent_examples)
