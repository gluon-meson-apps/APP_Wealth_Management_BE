from action.base import (
    Action,
    ActionResponse,
    GeneralResponse,
    ChatResponseAnswer,
    ResponseMessageType,
)
from nlu.intent_with_entity import Intent


class IntentAvailableCheckingAction(Action):
    def __init__(self, intent: Intent):
        self.intent = intent

    def get_name(self) -> str:
        return "intent_available_checking"

    async def run(self, context) -> ActionResponse:
        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=f"The intent '{self.intent.name}' is currently suspended.",
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
