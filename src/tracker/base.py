import threading
import time
from datetime import datetime, timedelta
from loguru import logger

import schedule

from tracker.context import ConversationContext


class ConversationTracker:
    def save_conversation(self, session_id: str, conversation_context: ConversationContext):
        raise NotImplementedError

    def load_conversation(self, session_id: str) -> ConversationContext:
        raise NotImplementedError

    def clear_inactive_conversations(self):
        raise NotImplementedError


def start_schedule():
    # 无限循环，直到程序手动停止
    while True:
        schedule.run_pending()
        time.sleep(10)


class BaseConversationTracker(ConversationTracker):

    def __init__(self):
        self.conversation_caches = {}
        # 每天固定时间执行clear_inactive_conversations函数
        schedule.every().day.at("00:00").do(self.clear_inactive_conversations)

        # 启动定时任务
        schedule_thread = threading.Thread(target=start_schedule)
        schedule_thread.start()

    def save_conversation(self, session_id: str, conversation_context: ConversationContext):
        self.conversation_caches[session_id] = conversation_context

    def load_conversation(self, session_id: str) -> ConversationContext:
        if session_id in self.conversation_caches:
            logger.info(f"session_id is {session_id}")
            conversation = self.conversation_caches[session_id]
            conversation.updated_at = datetime.now()
            return conversation
        return ConversationContext(current_user_input="", session_id=session_id)

    def clear_inactive_conversations(self):
        current_time = datetime.now()
        inactive_conversations = [session_id for session_id, conversation in self.conversation_caches.items()
                                  if (current_time - conversation.updated_at) > timedelta(hours=24)]
        for session_id in inactive_conversations:
            logger.info(f"clear history for {session_id}")
            del self.conversation_caches[session_id]
