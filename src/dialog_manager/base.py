import os
from typing import Any

from fastapi import UploadFile
from gluon_meson_sdk.dbs.milvus.milvus_connection import MilvusConnection
from gluon_meson_sdk.dbs.milvus.milvus_for_langchain import MilvusForLangchain
from gluon_meson_sdk.models.chat_model import ChatModel
from gluon_meson_sdk.models.embedding_model import EmbeddingModel
from loguru import logger

from action.context import ActionContext
from action.runner import ActionRunner, SimpleActionRunner
from llm.self_host import ChatModel as SelfHostChatModel
from nlu.forms import FormStore
from nlu.intent_config import IntentListConfig
from nlu.llm.entity import LLMEntityExtractor
from nlu.llm.intent import LLMIntentClassifier
from nlu.mlm.integrated import IntegratedNLU
from output_adapter.base import BaseOutputAdapter, OutputAdapter
from output_adapter.email_output_adapter import EmailOutputAdapter
from policy.base import BasePolicyManager
from policy.general import (
    AssistantPolicy,
    IntentFillingPolicy,
    EndDialoguePolicy,
    JumpOutPolicy,
    IntentChoosingPolicy,
)
from policy.slot_filling.slot_filling_policy import SlotFillingPolicy
from prompt_manager.base import BasePromptManager
from reasoner.base import Reasoner
from reasoner.llm_reasoner import LlmReasoner
from third_system.search_entity import SearchResponse
from tracker.HistorySummarizer import HistorySummarizer
from tracker.base import BaseConversationTracker, ConversationTracker
from tracker.context import ConversationContext


class BaseDialogManager:
    def __init__(
        self,
        conversation_tracker: ConversationTracker,
        reasoner: Reasoner,
        action_runner: ActionRunner,
        output_adapters: list[OutputAdapter],
        history_summarizer: HistorySummarizer,
    ):
        self.conversation_tracker = conversation_tracker
        self.action_runner = action_runner
        self.output_adapters = output_adapters
        self.reasoner = reasoner
        self.history_summarizer = history_summarizer

    async def greet(self, user_id: str) -> Any:
        conversation = self.conversation_tracker.load_conversation(user_id)

        action = self.reasoner.greet(conversation)
        action_response = self.action_runner.run(action, ActionContext(conversation))
        response = await self.output_adapter.process_output(action_response)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response

    async def handle_message(
        self,
        message: Any,
        session_id: str,
        files: list[UploadFile] = None,
        file_contents: list[SearchResponse] = None,
        is_email_request=False,
    ) -> tuple[Any, ConversationContext]:
        file_name = None
        if files is None:
            files = []
        if file_contents is None:
            file_contents = []
        else:
            items = file_contents[0].items
            if len(items) > 0:
                file_name = items[0].meta__reference.meta__source_name
        self.conversation_tracker.clear_inactive_conversations()
        conversation = self.conversation_tracker.load_conversation(session_id)
        conversation.start_one_chat()
        logger.info(f"current intent is {conversation.current_intent}")
        conversation.current_user_input = message
        conversation.append_user_history(message, file_name)
        conversation.add_files(files)
        conversation.add_file_contents(file_contents)
        conversation.set_email_request(is_email_request)

        plan = await self.reasoner.think(conversation)

        action_response = await self.action_runner.run(plan.action, ActionContext(conversation))
        for output_adapter in self.output_adapters:
            action_response = await output_adapter.process_output(action_response, conversation)
        response = action_response
        conversation.append_assistant_history(response.answer)
        await self.history_summarizer.summarize_history(conversation)
        self.conversation_tracker.save_conversation(conversation.session_id, conversation)
        conversation.current_round += 1
        return response, conversation


class DialogManagerFactory:
    @classmethod
    def create_dialog_manager(cls):
        model_type = "azure-gpt-3.5-2"
        action_model_type = "azure-gpt-3.5-2"

        pwd = os.path.dirname(os.path.abspath(__file__))
        intent_config_file_path = os.path.join(pwd, "../", "resources", "scenes")
        pwd = os.path.dirname(os.path.abspath(__file__))
        prompt_template_folder = os.path.join(pwd, "..", "resources", "prompt_templates")

        reasoner = cls.create_reasoner(
            model_type,
            action_model_type,
            intent_config_file_path,
            prompt_template_folder,
        )

        return BaseDialogManager(
            BaseConversationTracker(),
            reasoner,
            SimpleActionRunner(),
            [BaseOutputAdapter(), EmailOutputAdapter()],
            HistorySummarizer()
        )

    @classmethod
    def create_reasoner(
        cls,
        model_type,
        action_model_type,
        intent_config_file_path,
        prompt_template_folder,
    ):
        embedding_model = EmbeddingModel()

        intent_list_config = IntentListConfig.from_scenes(intent_config_file_path)
        prompt_manager = BasePromptManager(prompt_template_folder)

        classifier = LLMIntentClassifier(
            chat_model=SelfHostChatModel(),
            embedding_model=embedding_model,
            milvus_for_langchain=MilvusForLangchain(embedding_model, MilvusConnection()),
            intent_list_config=intent_list_config,
            model_type=model_type,
            prompt_manager=prompt_manager,
        )

        form_store = FormStore(intent_list_config)
        entity_extractor = LLMEntityExtractor(
            form_store,
            ChatModel(),
            model_type=model_type,
            prompt_manager=prompt_manager,
        )

        slot_filling_policy = SlotFillingPolicy(prompt_manager, form_store)
        assitant_policy = AssistantPolicy(prompt_manager, form_store)
        intent_filling_policy = IntentFillingPolicy(prompt_manager, form_store)
        end_dialogue_policy = EndDialoguePolicy(prompt_manager, form_store)
        jump_out_policy = JumpOutPolicy(prompt_manager, form_store)
        intent_choosing_policy = IntentChoosingPolicy(prompt_manager)

        policy_manager = BasePolicyManager(
            policies=[
                end_dialogue_policy,
                jump_out_policy,
                intent_choosing_policy,
                intent_filling_policy,
                slot_filling_policy,
                assitant_policy,
            ],
            prompt_manager=prompt_manager,
            action_model_type=action_model_type,
        )
        nlu = IntegratedNLU(classifier, entity_extractor)

        reasoner = LlmReasoner(nlu, policy_manager, model_type)
        return reasoner
