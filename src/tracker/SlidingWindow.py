from tracker.SummarizeHistory import SummarizeHistory
from tracker.context import ConversationContext

sliding_count = 5


class SlidingWindow:
    def __init__(self):
        self.history_summarizer = SummarizeHistory()

    async def chat_history_to_window(self, conversation: ConversationContext):
        history = conversation.get_unsummarized_history()
        # TODO: count history or count token
        if len(history) >= sliding_count:
            if conversation.summarized_history:
                history.insert(0, {"role": "system", "content": conversation.summarized_history})
            summarized_history = await self.history_summarizer.summarize(history, conversation.session_id)
            conversation.summarized_history = summarized_history
            conversation.history.flag_history_summarized(len(history))

        return conversation
