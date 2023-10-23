from typing import List, Any

from nlu.intent_with_entity import Intent


class History:
    def __init__(self, histories: List[dict[str, Any]]):
        self.histories = histories

    def add_history(self, role: str, message: str):
        self.histories.append({'role': role, 'content': message})

    def format_to_string(self):
        return '\n'.join([f'{entry["role"]}: {entry["content"]}' for entry in self.histories])


class ConversationContext:
    def __init__(self, current_user_input: str, current_user_intent: Intent = None):
        self.current_user_input = current_user_input
        self.current_intent = current_user_intent
        self.current_enriched_user_input = None
        self.history = History([])

    def get_history(self) -> History:
        return self.history

    def append_history(self, role: str, message: str):
        self.history.add_history(role, message)

if __name__ == '__main__':
    context = ConversationContext('你好')
    context.append_history('user', '你好')
    context.append_history('assistant', '你好')
    print(context.get_history().format_to_string())