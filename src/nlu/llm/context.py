from conversation_tracker.context import ConversationContext, History


class FullLlmConversationContext(ConversationContext):
    def __init__(self, conversation_context: ConversationContext):
        self.conversation_context = conversation_context

    def get_current_user_input(self):
        return self.conversation_context.current_user_input

    def get_current_intent(self):
        return self.conversation_context.current_intent

    def get_history(self) -> History:
        return self.conversation_context.get_history()

    def append_history(self, role: str, message: str):
        self.conversation_context.append_history(role, message)