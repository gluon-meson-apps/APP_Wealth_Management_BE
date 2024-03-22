from typing import Sequence

from policy.slot_filling.base_slot_checker import BaseSlotChecker, SlotCheckResult


class OneSlotSequenceChecker(BaseSlotChecker):
    def __init__(self, slot_sequence: Sequence[str]):
        self.slot_sequence = set(slot_sequence)

    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        return not self.get_missed_slots(real_slots)[0]

    def calc_missing_weight(self, missed_len: int, total_len: int) -> float:
        if total_len == 0:
            return 0
        return missed_len + missed_len / total_len

    def get_unsorted_missed_slots(self, real_slots: Sequence[str]) -> Sequence[SlotCheckResult]:
        real_slots = set(real_slots)
        missed_slots = list(self.slot_sequence - real_slots)
        missed_len = len(missed_slots)

        return [
            SlotCheckResult(
                missed_slots=missed_slots, missing_weight=self.calc_missing_weight(missed_len, len(self.slot_sequence))
            )
        ]

    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        return [list(self.slot_sequence - set(real_slots))]


class MultiSlotSequenceChecker(BaseSlotChecker):
    def __init__(self, slot_sequences: Sequence[Sequence[str]]):
        self.slot_sequences_checker = [OneSlotSequenceChecker(slot_sequence) for slot_sequence in slot_sequences]

    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        return any(checker.check_slot_missing(real_slots) for checker in self.slot_sequences_checker)

    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        sorted_missed_slot_result = sorted(
            [checker.get_unsorted_missed_slots(real_slots)[0] for checker in self.slot_sequences_checker],
            key=lambda x: x.missing_weight,
        )
        return [slot_result.missed_slots for slot_result in sorted_missed_slot_result]

    def get_unsorted_missed_slots(self, real_slots: Sequence[str]) -> Sequence[SlotCheckResult]:
        return [checker.get_unsorted_missed_slots(real_slots)[0] for checker in self.slot_sequences_checker]
