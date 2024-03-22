from abc import abstractmethod
from typing import Union

from action.actions.general import ChitChatAction
from action.actions.tb_guru.br_file_qa_action import BrFileQAAction
from action.actions.tb_guru.br_file_validation import BrFileValidation
from action.actions.tb_guru.file_batch_qa import FileBatchAction
from action.actions.tb_guru.gps_product_check import GPSProductCheckAction
from action.actions.tb_guru.rma_checking import RMACheckingAction
from action.actions.tb_guru.rma_lc_acceptable import LCAcceptableAction
from action.actions.tb_guru.standard_pricing_check_action import StandardPricingCheckAction
from action.actions.tb_guru.file_validation import FileValidation
from action.actions.tb_guru.summary_and_translation import SummarizeAndTranslate
from action.actions.tb_guru.wcs_data_query import WcsDataQuery
from action.actions.tb_guru.br_extenstion_qa import BRExtensionQAAction
from action.actions.tb_guru.rma_pricing import RMAPricingAction
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
action_repository.save(ChitChatAction())
action_repository.save(FileBatchAction())
action_repository.save(StandardPricingCheckAction())
action_repository.save(BrFileQAAction())
action_repository.save(RMACheckingAction())
action_repository.save(LCAcceptableAction())
action_repository.save(FileValidation())
action_repository.save(WcsDataQuery())
action_repository.save(GPSProductCheckAction())
action_repository.save(BrFileValidation())
action_repository.save(BRExtensionQAAction())
action_repository.save(SummarizeAndTranslate())
action_repository.save(RMAPricingAction())
