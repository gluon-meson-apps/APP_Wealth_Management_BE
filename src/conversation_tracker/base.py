from conversation_tracker.context import ConversationContext


class ConversationTracker:
    def save_conversation(self, id: str, conversation_context: ConversationContext):
        raise NotImplementedError

    def load_conversation(self, id: str) -> ConversationContext:
        raise NotImplementedError


class BaseConversationTracker(ConversationTracker):

    def __init__(self):
        self.conversation_caches = {}

    def save_conversation(self, id: str, conversation_context: ConversationContext):
        self.conversation_caches[id] = conversation_context

    def load_conversation(self, id: str) -> ConversationContext:
        if id in self.conversation_caches:
            conversation = self.conversation_caches[id]
            return conversation
        return ConversationContext(current_user_input="", user_id=id)
