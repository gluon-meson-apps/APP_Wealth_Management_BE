from typing import Any

from action_runner.base import ActionRunner
from action_runner.context import ActionContext
from conversation_tracker.base import ConversationTracker
from output_adapter.base import OutputAdapter
from reasoner.base import Reasoner


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

    def handle_message(self, message: Any, user_id: str) -> Any:
        conversation = self.conversation_tracker.load_conversation(user_id)
        conversation.current_user_input = message
        conversation.append_history('user', message)
        conversation.current_enriched_user_input = conversation.current_user_input

        plan = self.reasoner.think(conversation)

        action_response = self.action_runner.run(plan.action, ActionContext(conversation))
        response = self.output_adapter.process_output(action_response)
        conversation.append_history('assistant', response.text)
        self.conversation_tracker.save_conversation(user_id, conversation)
        return response.text
