import json

from tracker.context import ConversationContext


def format_entities_for_search(conversation: ConversationContext, exclude_keys: list[str] = None) -> str:
    return json.dumps(
        {
            key: value
            for key, value in conversation.get_simplified_entities().items()
            if exclude_keys and key not in exclude_keys
        }
    )
