from abc import ABC, abstractmethod
from typing import Sequence

from pydantic import BaseModel


class SlotCheckResult(BaseModel):
    missed_slots: Sequence[str]
    missing_weight: float


class BaseSlotChecker(ABC):
    @abstractmethod
    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        pass

    @abstractmethod
    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        pass

    @abstractmethod
    def get_unsorted_missed_slots(self, real_slots: Sequence[str]) -> Sequence[SlotCheckResult]:
        pass
