from abc import abstractmethod
from typing import Union

from action.actions.general import ChitChatAction, QAAction, FileValidationAction
from action.base import Action
from llm.self_host import ChatModel


class ActionRepository:
    @abstractmethod
    def save(self, action: Action):
        pass

    @abstractmethod
    def find_by_name(self, name) -> Union[Action, None]:
        pass


class MemoryBasedActionRepository(ActionRepository):
    def __init__(self):
        self.actions = {}

    def save(self, action: Action):
        self.actions[action.get_name()] = action

    def find_by_name(self, name) -> Union[Action, None]:
        if name not in self.actions:
            return None
        return self.actions[name]

action_repository = MemoryBasedActionRepository()
action_repository.save(ChitChatAction("azure-gpt-3.5-2", ChatModel()))
action_repository.save(QAAction("azure-gpt-3.5-2", ChatModel()))
action_repository.save(FileValidationAction("azure-gpt-3.5-2", ChatModel()))
