from typing import Sequence

from nlu.forms import Form
from nlu.intent_with_entity import Slot, SlotType
from policy.slot_filling.base_slot_checker import BaseSlotChecker
from policy.slot_filling.expression_slot_checker import ExpressionSlotSequenceChecker
from policy.slot_filling.slot_sequence_checker import OneSlotSequenceChecker


class SlotChecker:
    def __init__(self, form: Form, possible_slots: Sequence[str]):
        if form.has_slot_expression():
            self.real_checker: BaseSlotChecker = ExpressionSlotSequenceChecker(form.slot_expression)
        else:
            self.real_checker: BaseSlotChecker = OneSlotSequenceChecker(
                [slot.name for slot in form.slots if not slot.optional and slot.slot_type != SlotType.BOOLEAN]
            )
        self.form = form
        self.possible_slots = possible_slots

    def slot_is_missing(self) -> bool:
        return not self.real_checker.check_slot_missing(self.possible_slots)

    def get_missed_slots(self) -> Sequence[Sequence[Slot]]:
        # self.real_checker.get_missed_slots(self.possible_slots)
        missed_slots = self.real_checker.get_missed_slots(self.possible_slots)
        return [self.form.get_slot_by_names(slots) for slots in missed_slots]
