import ast
from typing import Sequence

from policy.slot_filling.base_slot_checker import BaseSlotChecker, SlotCheckResult
from policy.slot_filling.slot_expression_visitor import SlotExpressionVisitor
from policy.slot_filling.slot_sequence_checker import MultiSlotSequenceChecker


class ExpressionSlotSequenceChecker(BaseSlotChecker):
    def __init__(self, expression: str):
        self.slot_sequences_checker = MultiSlotSequenceChecker(self.parse_expression(expression))
        self.expression = expression

    @classmethod
    def parse_expression(cls, expression) -> list[list[str]]:
        expression_ast = ast.parse(expression)
        visitor = SlotExpressionVisitor()
        visitor.visit(expression_ast)
        return visitor.new_items[0][0]

    def check_slot_missing(self, real_slots: Sequence[str]) -> bool:
        return self.slot_sequences_checker.check_slot_missing(real_slots)

    def get_missed_slots(self, real_slots: Sequence[str]) -> Sequence[Sequence[str]]:
        return self.slot_sequences_checker.get_missed_slots(real_slots)

    def get_unsorted_missed_slots(self, real_slots: Sequence[str]) -> Sequence[SlotCheckResult]:
        return self.slot_sequences_checker.get_unsorted_missed_slots(real_slots)
