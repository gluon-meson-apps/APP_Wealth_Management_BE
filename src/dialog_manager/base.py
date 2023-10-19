from typing import Any

from action_runner.base import ActionRunner
from action_runner.context import ActionContext
from conversation_tracker.base import ConversationTracker
from input_enricher.base import InputEnricher
from nlu.base import Nlu
from output_adapter.base import OutputAdapter
from policy_manager.base import PolicyManager


class BaseDialogManager:
    def __init__(self, conversation_tracker: ConversationTracker, input_enricher: InputEnricher, nlu: Nlu,
                 policy_manager: PolicyManager,
                 action_runner: ActionRunner, output_adapter: OutputAdapter, model_type: str):
        self.conversation_tracker = conversation_tracker
        self.input_enricher = input_enricher
        self.nlu = nlu
        self.policy_manager = policy_manager
        self.action_runner = action_runner
        self.output_adapter = output_adapter
        self.model_type = model_type

    def handle_message(self, message: Any, user_id: str) -> Any:
        conversation = self.conversation_tracker.load_conversation(user_id)
        conversation.current_user_input = message
        conversation.append_history('user', message)
        enriched_input = self.input_enricher.enrich(conversation.current_user_input)
        conversation.current_enriched_user_input = enriched_input
        intent = self.nlu.extract_intents_and_entities(conversation)
        # todo: 需要补充一轮槽位，根据识别的意图，获取表单，然后从表单中获取槽位，有一些槽位是可以自动填充的，比如查天气，默认是今天，开灯的话，根据所对话的智能音箱所处的房间，自动填充房间。
        action = self.policy_manager.get_action(intent, conversation, self.model_type)
        action_response = self.action_runner.run(action, ActionContext(conversation))
        response = self.output_adapter.process_output(action_response)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response
