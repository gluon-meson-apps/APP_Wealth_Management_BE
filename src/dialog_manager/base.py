from typing import Any

from action_runner.base import ActionRunner
from action_runner.context import ActionContext
from conversation_tracker.base import ConversationTracker
from input_enricher.base import InputEnricher
from output_adapter.base import OutputAdapter
from reasoner.base import Reasoner


class BaseDialogManager:
    def __init__(self, conversation_tracker: ConversationTracker, input_enricher: InputEnricher, reasoner: Reasoner,
                 action_runner: ActionRunner, output_adapter: OutputAdapter):
        self.conversation_tracker = conversation_tracker
        self.input_enricher = input_enricher
        self.action_runner = action_runner
        self.output_adapter = output_adapter
        self.reasoner = reasoner

    def handle_message(self, message: Any, user_id: str) -> Any:
        conversation = self.conversation_tracker.load_conversation(user_id)
        conversation.current_user_input = message
        conversation.append_history('user', message)
        enriched_input = self.input_enricher.enrich(conversation.current_user_input)
        conversation.current_enriched_user_input = enriched_input

        plan = self.reasoner.think(conversation)

        action_response = self.action_runner.run(plan.action, ActionContext(conversation))
        response = self.output_adapter.process_output(action_response)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response
