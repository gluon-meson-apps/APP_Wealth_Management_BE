from conversation_tracker.context import ConversationContext


class ConversationTracker:
    def save_conversation(self, id: str, conversation_context: ConversationContext):
        raise NotImplementedError

    def load_conversation(self, id: str) -> ConversationContext:
        raise NotImplementedError


class BaseConversationTracker(ConversationTracker):
    def save_conversation(self, id: str, conversation_context: ConversationContext):
        pass

    def load_conversation(self, id: str) -> ConversationContext:
        return ConversationContext("")
