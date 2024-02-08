from functools import reduce

import itertools
import ast


class SlotExpressionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.new_items = [[]]
        self.available_slots = [[]]
        self.flat_slot_conditions = [[]]

    @classmethod
    def merge_or(cls, to_be_merge: list[list[str]], items: list[list[str]]):
        # [[a], [aa]] [[b], [bb]] => [[a], [aa], [b], [bb]]
        return to_be_merge + items

    @classmethod
    def merge_and(cls, to_be_merge: list[list[str]], items: list[list[str]]):
        # [[a], [aa]] [[b], [bb]] => [[a, b], [a, bb], [aa, b], [aa, bb]]
        return [reduce(lambda x, y: x + y, i) for i in itertools.product(to_be_merge, items)]

    def modify_sub_expression(self, items: list[list[list[str]]], op):
        print(f"merge sub expression: {items}")
        if isinstance(op, ast.And):
            flat_slot_conditions = [[]]
            for item in items:
                flat_slot_conditions = self.merge_and(item, flat_slot_conditions)
        elif isinstance(op, ast.Or):
            flat_slot_conditions = []
            for item in items:
                flat_slot_conditions = self.merge_or(item, flat_slot_conditions)
        else:
            raise ValueError(f"Unknown op: {op}")
        return flat_slot_conditions

    def visit_Str(self, node):
        self.new_items[-1].append([[node.s]])
        self.generic_visit(node)

    def visit_Name(self, node):
        self.new_items[-1].append([[node.id]])
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.new_items.append([])
        self.generic_visit(node)
        new_items = self.new_items.pop()
        flat_slot_conditions = self.modify_sub_expression(new_items, node.op)
        print(f"merged : {flat_slot_conditions}")
        self.new_items[-1].append(flat_slot_conditions)
