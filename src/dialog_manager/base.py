from typing import Any

from action_runner.base import ActionRunner, BaseActionRunner
from action_runner.context import ActionContext
from conversation_tracker.base import ConversationTracker, BaseConversationTracker
from input_enricher.base import InputEnricher, BaseInputEnricher
from nlu.base import Nlu, BaseNlu
from output_adapter.base import OutputAdapter, BaseOutputAdapter
from policy_manager.base import PolicyManager, BasePolicyManager


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
        enriched_input = self.input_enricher.enrich(conversation.current_user_input)
        intent = self.nlu.extract_intents_and_entities(enriched_input)
        action = self.policy_manager.get_action(intent)
        action_response = self.action_runner.run(action, ActionContext())
        response = self.output_adapter.process_output(action_response)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response


if __name__ == '__main__':
    # construct BaseDialogManager
    # call handle_message

    BaseDialogManager(BaseConversationTracker(), BaseInputEnricher(), BaseNlu(), BasePolicyManager([]),
                      BaseActionRunner(), BaseOutputAdapter()).handle_message("hi", "123")
