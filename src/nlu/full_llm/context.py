from conversation_tracker.context import ConversationContext


class FullLlmConversationContext:
    def __init__(self, conversation_context: ConversationContext):
        self.conversation_context = conversation_context

    def get_current_user_input(self):
        return self.conversation_context.current_user_input

    def get_current_intent(self):
        return self.conversation_context.current_intent
