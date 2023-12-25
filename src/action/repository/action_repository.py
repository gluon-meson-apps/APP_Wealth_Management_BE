from abc import abstractmethod

from action.base import Action


class ActionRepository:
    @abstractmethod
    def save(self, action: Action):
        pass

    @abstractmethod
    def find_by_name(self, name) -> Action:
        pass


class MemoryBasedActionRepository(ActionRepository):
    def __init__(self):
        self.actions = {}

    def save(self, action: Action):
        self.actions[action.get_name()] = action

    def find_by_name(self, name) -> Action:
        return self.actions[name]

action_repository = MemoryBasedActionRepository()