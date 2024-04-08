from abc import abstractmethod
from typing import Union

from action.actions.general import ChitChatAction
from action.actions.wealth_management.research_report_navigator_action import ResearchReportNavigatorAction
from action.base import Action


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
action_repository.save(ResearchReportNavigatorAction())
action_repository.save(ChitChatAction())