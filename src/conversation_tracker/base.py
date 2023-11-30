from datetime import datetime, timedelta

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
            conversation.updated_at = datetime.now()
            return conversation
        return ConversationContext(current_user_input="", session_id=id)

    def clear_inactive_conversations(self):
        current_time = datetime.now()
        inactive_conversations = [id for id, conversation in self.conversation_caches.items()
                                  if (current_time - conversation.updated_at) > timedelta(hours=24)]
        for id in inactive_conversations:
            del self.conversation_caches[id]
