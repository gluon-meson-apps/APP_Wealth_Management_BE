from abc import ABC, abstractmethod
from typing import Sequence


class BaseSlotChecker(ABC):
    @abstractmethod
    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        pass

    @abstractmethod
    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        pass
