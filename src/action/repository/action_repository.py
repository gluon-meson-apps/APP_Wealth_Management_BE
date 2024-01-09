from abc import abstractmethod
from typing import Union

from action.actions.general import ChitChatAction, FileValidationAction
from action.actions.tb_guru.br_file_qa_action import BrFileQAAction
from action.actions.tb_guru.file_batch_qa import FileBatchAction
from action.actions.tb_guru.standard_pricing_check_action import StandardPricingCheckAction
from action.actions.tb_guru.letter_of_credit_advising import LetterOfCreditAdvisingAction
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
action_repository.save(FileBatchAction())
action_repository.save(FileValidationAction("azure-gpt-3.5-2", ChatModel()))
action_repository.save(StandardPricingCheckAction())
action_repository.save(BrFileQAAction())
action_repository.save(LetterOfCreditAdvisingAction())
