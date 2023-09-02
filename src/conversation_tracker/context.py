class ConversationContext:
    def __init__(self, current_user_input: str, current_user_intent: str = None):
        self.current_user_input = current_user_input
        self.current_intent = current_user_intent
