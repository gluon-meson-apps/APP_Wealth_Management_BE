import unittest
from datetime import datetime, timedelta
from tracker.base import BaseConversationTracker
from tracker.context import ConversationContext

class TestConversation(unittest.TestCase):

    def test_save_conversation(self):
        tracker = BaseConversationTracker()
        session_id = "123"
        context = ConversationContext("Hello", session_id)
        tracker.save_conversation(session_id, context)
        self.assertIn(session_id, tracker.conversation_caches)
        self.assertEqual(tracker.conversation_caches[session_id].current_user_input, "Hello")

    def test_load_conversation_with_valid_session_id(self):
        tracker = BaseConversationTracker()
        session_id = "123"
        context = ConversationContext("Hello", session_id)
        tracker.save_conversation(session_id, context)
        loaded_context = tracker.load_conversation(session_id)
        self.assertEqual(loaded_context.current_user_input, "Hello")
        self.assertEqual(loaded_context.session_id, session_id)

    def test_load_conversation_with_invalid_session_id(self):
        tracker = BaseConversationTracker()
        loaded_context = tracker.load_conversation("invalid_id")
        self.assertEqual(loaded_context.current_user_input, "")
        self.assertEqual(loaded_context.session_id, "invalid_id")

    def test_clear_inactive_conversations(self):
        tracker = BaseConversationTracker()
        session_id = "456"
        context = ConversationContext("Hi", session_id)
        tracker.save_conversation(session_id, context)
        # 模拟时间流逝
        tracker.conversation_caches[session_id].updated_at = datetime.now() - timedelta(hours=25)
        tracker.clear_inactive_conversations()
        self.assertNotIn(session_id, tracker.conversation_caches)

if __name__ == '__main__':
    unittest.main()