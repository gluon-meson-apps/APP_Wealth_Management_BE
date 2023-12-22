import os
from typing import Any

from action.runner import ActionRunner, SimpleActionRunner
from action.context import ActionContext
from tracker.base import BaseConversationTracker, ConversationTracker
from output_adapter.base import BaseOutputAdapter, OutputAdapter
from reasoner.base import Reasoner
from loguru import logger
from nlu.forms import FormStore

from nlu.mlm.entity import MLMEntityExtractor
from nlu.mlm.intent import MLMIntentClassifier, IntentListConfig
from policy.base import BasePolicyManager
from policy.general import AssistantPolicy, IntentFillingPolicy, SlotFillingPolicy, EndDialoguePolicy, JumpOutPolicy
from prompt_manager.base import BasePromptManager
from reasoner.llm_reasoner import LlmReasoner


class BaseDialogManager:
    def __init__(self, conversation_tracker: ConversationTracker, reasoner: Reasoner,
                 action_runner: ActionRunner, output_adapter: OutputAdapter):
        self.conversation_tracker = conversation_tracker
        self.action_runner = action_runner
        self.output_adapter = output_adapter
        self.reasoner = reasoner

    def greet(self, user_id: str) -> Any:
        conversation = self.conversation_tracker.load_conversation(user_id)

        action = self.reasoner.greet(conversation)
        action_response = self.action_runner.run(action, ActionContext(conversation))
        response = self.output_adapter.process_output(action_response)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response

    def handle_message(self, message: Any, session_id: str) -> Any:
        self.conversation_tracker.clear_inactive_conversations()
        conversation = self.conversation_tracker.load_conversation(session_id)
        logger.info(f"current intent is {conversation.current_intent}")
        conversation.current_user_input = message
        conversation.append_user_history(message)

        plan = self.reasoner.think(conversation)

        action_response = self.action_runner.run(plan.action, ActionContext(conversation))
        response = self.output_adapter.process_output(action_response)
        conversation.append_assistant_history(response.answer)
        self.conversation_tracker.save_conversation(conversation.session_id, conversation)
        conversation.current_round += 1
        return response, conversation

class DialogManagerFactory:
    @staticmethod
    def create_dialog_manager():
        model_type = "chatglm"
        action_model_type = "chatglm"

        pwd = os.path.dirname(os.path.abspath(__file__))
        prompt_template_folder = os.path.join(pwd, '../', 'resources', 'prompt_templates')
        intent_config_file_path = os.path.join(pwd, '../', 'resources', 'scenes')

        intent_list_config = IntentListConfig.from_scenes(intent_config_file_path)
        prompt_manager = BasePromptManager(prompt_template_folder)

        classifier = MLMIntentClassifier(intent_list_config)
        form_store = FormStore(intent_list_config)
        entity_extractor = MLMEntityExtractor(form_store)

        slot_filling_policy = SlotFillingPolicy(prompt_manager, form_store)
        assitant_policy = AssistantPolicy(prompt_manager, form_store)
        intent_filling_policy = IntentFillingPolicy(prompt_manager, form_store)
        end_dialogue_policy = EndDialoguePolicy(prompt_manager, form_store)
        jump_out_policy = JumpOutPolicy(prompt_manager, form_store)

        policy_manager = BasePolicyManager(
            policies=[end_dialogue_policy, jump_out_policy, intent_filling_policy, slot_filling_policy, assitant_policy],
            prompt_manager=prompt_manager,
            action_model_type=action_model_type
        )
        reasoner = LlmReasoner(classifier, entity_extractor, policy_manager, model_type)
        return BaseDialogManager(BaseConversationTracker(), reasoner, SimpleActionRunner(), BaseOutputAdapter())
