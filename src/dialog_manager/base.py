from typing import Any

from action_runner.base import ActionRunner, BaseActionRunner, SimpleActionRunner
from action_runner.context import ActionContext
from conversation_tracker.base import ConversationTracker, BaseConversationTracker
from input_enricher.base import InputEnricher, BaseInputEnricher
from nlu.base import Nlu, BaseNlu
from nlu.forms import FormStore
from nlu.llm.entity import EntityExtractor
from nlu.llm.intent import IntentClassifier
from nlu.llm.llm_nlu import LLMNlu
from output_adapter.base import OutputAdapter, BaseOutputAdapter
from policy_manager.base import PolicyManager, BasePolicyManager
from policy_manager.policy import SlotCheckPolicy, SmartHomeOperatingPolicy
from sdk.src.gluon_meson_sdk.dbs.milvus.milvus_connection import MilvusConnection
from sdk.src.gluon_meson_sdk.dbs.milvus.milvus_for_langchain import MilvusForLangchain
from sdk.src.gluon_meson_sdk.models.chat_model import ChatModel
from sdk.src.gluon_meson_sdk.models.embedding_model import EmbeddingModel


class BaseDialogManager:
    def __init__(self, conversation_tracker: ConversationTracker, input_enricher: InputEnricher, nlu: Nlu,
                 policy_manager: PolicyManager,
                 action_runner: ActionRunner, output_adapter: OutputAdapter):
        self.conversation_tracker = conversation_tracker
        self.input_enricher = input_enricher
        self.nlu = nlu
        self.policy_manager = policy_manager
        self.action_runner = action_runner
        self.output_adapter = output_adapter

    def handle_message(self, message: Any, user_id: str) -> Any:
        conversation = self.conversation_tracker.load_conversation(user_id)
        conversation.current_user_input = message
        conversation.append_history('user', message)
        enriched_input = self.input_enricher.enrich(conversation.current_user_input)
        conversation.current_enriched_user_input = enriched_input
        intent = self.nlu.extract_intents_and_entities(conversation)
        action = self.policy_manager.get_action(intent, conversation)
        action_response = self.action_runner.run(action, ActionContext(conversation))
        response = self.output_adapter.process_output(action_response)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response


if __name__ == '__main__':
    # construct BaseDialogManager
    # call handle_message

    embedding_model = EmbeddingModel()
    classifier = IntentClassifier(ChatModel(), embedding_model, MilvusForLangchain(embedding_model, MilvusConnection()))
    form_store = FormStore()
    result = BaseDialogManager(BaseConversationTracker(), BaseInputEnricher(), LLMNlu(classifier, EntityExtractor(form_store, ChatModel())), BasePolicyManager([SlotCheckPolicy(form_store), SmartHomeOperatingPolicy()]),
                      SimpleActionRunner(), BaseOutputAdapter()).handle_message("打开灯", "123")
    print(result)
