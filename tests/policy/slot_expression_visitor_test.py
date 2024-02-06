import pytest

from policy.slot_filling.slot_expression_visitor import SlotExpressionVisitor


@pytest.mark.parametrize(
"to_be_merge, items, expected",
[
    ([['a'], ['aa']], [['b'], ['bb']], [['a', 'b'], ['a', 'bb'], ['aa', 'b'], ['aa', 'bb']]),
    ([['a', 'c', 'd']], [['b'], ['bb']], [['a', 'c', 'd', 'b'], ['a', 'c', 'd', 'bb']]),
]
)
def test_merge_and(to_be_merge, items, expected):
    actual = SlotExpressionVisitor.merge_and(to_be_merge, items)
    assert actual== expected

@pytest.mark.parametrize(
"to_be_merge, items, expected",
[
    ([['a'], ['aa']], [['b'], ['bb']], [['a'], ['aa'], ['b'], ['bb']]),
    ([['a', 'c', 'd']], [['b'], ['bb']], [['a', 'c', 'd'], ['b'], ['bb']]),
]
)
def test_merge_or(to_be_merge, items, expected):
    actual = SlotExpressionVisitor.merge_or(to_be_merge, items)
    assert actual == expected
