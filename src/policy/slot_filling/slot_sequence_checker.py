from typing import Sequence

from policy.slot_filling.base_slot_checker import BaseSlotChecker


class OneSlotSequenceChecker(BaseSlotChecker):
    def __init__(self, slot_sequence: Sequence[str]):
        self.slot_sequence = set(slot_sequence)

    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        return not self.get_missed_slots(real_slots)[0]

    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        return [list(self.slot_sequence - set(real_slots))]


class MultiSlotSequenceChecker(BaseSlotChecker):
    def __init__(self, slot_sequences: Sequence[Sequence[str]]):
        self.slot_sequences_checker = [OneSlotSequenceChecker(slot_sequence) for slot_sequence in slot_sequences]

    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        return any(checker.check_slot_missing(real_slots) for checker in self.slot_sequences_checker)

    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        return sorted([checker.get_missed_slots(real_slots)[0] for checker in self.slot_sequences_checker], key=len)
