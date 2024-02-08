import ast
from typing import Sequence

import pytest

from policy.slot_filling.expression_slot_checker import ExpressionSlotSequenceChecker


@pytest.mark.parametrize(
    "test_name, expression, slot_names, expected",
    [
        # one layer
        ("one layer exact match", "'a' and 'b' and 'c'", ["a", "b", "c"], True),
        ("one layer match or any", "a or b or c", ["a"], True),
        ("one layer match or any2", "a or b or c", ["b"], True),
        ("one layer match or any3", "a or b or c", ["c"], True),

        ("one layer not match with one missing", "a and b and c", ["a", "b"], False),

        # two layers
        ("two layers exact match", "a and (b or bb) and c", ["a", "b", "bb", "c"], True),
        ("two layers match each in layer2 or", "a and (b or bb) and c", ["a", "b", "c"], True),
        ("two layers match each in layer2 or case2", "a and (b or bb) and c", ["a", "bb", "c"], True),
        ("two layers match all overflow", "a and (b or bb) and c", ["a", "b", "c", "d"], True),
        ("two layers match layer1 or", "a or (b and bb) or c", ["a"], True),
        ("two layers match layer1 or case2", "a or (b and bb) or c", ["b", "bb"], True),
        ("two layers match layer1 or case3", "a or (b and bb) or c", ["c"], True),
        ("two layers not match miss one", "a and (b or bb) and c", ["a", "b"], False),
        ("two layers not match miss one case 2", "a and (b or bb) and c", ["a", "b", "bb"], False),
        ("two layers not match one different element", "a and (b or bb) and c", ["a", "bb", "d"], False),
        ("two layers not match layer2 and", "a or (b and bb) or c", ["b"], False),

        # three layers
        ("three layers exact match", "a and (b or (bb and bbb)) and c", ["a", "b", "bb", "bbb", "c"], True),
        ("three layers match only one element in layer2 or", "a and (b or (bb and bbb)) and c", ["a", "b", "c"], True),
        ("three layers match only one element in layer2 or case2", "a and (b or (bb and bbb)) and c", ["a", "b", "c", "d"], True),
        ("three layers match only one element in layer2 or|all in layer3 and", "a and (b or (bb and bbb)) and c", ["a", "bb", "bbb", "c"], True),
        ("three layers match layer1 or case1", "a or (b and (bb or bbb)) or c", ["a"], True),
        ("three layers match layer1 or case2", "a or (b and (bb or bbb)) or c", ["c"], True),
        ("three layers match only one element in layer1 or | layer2 and | layer3 or case1", "a or (b and (bb or bbb)) or c", ["b", "bb"], True),
        ("three layers match only one element in layer1 or | layer2 and | layer3 or case2", "a or (b and (bb or bbb)) or c", ["b", "bbb"], True),
        ("three layers match only one element in layer1 or | layer2 and | layer3 or case3", "a or (b and (bb or bbb)) or c", ["b", "bb", "bbb"], True),

        ("three layers not match layer1 and miss 1 element case1", "a and (b or (bb and bbb)) and c", ["a", "b"], False),
        ("three layers not match layer1 and miss 1 element case2", "a and (b or (bb and bbb)) and c", ["a", "b", "bb"], False),
        ("three layers not match layer1 and miss 1 element case3", "a and (b or (bb and bbb)) and c", ["a", "b", "bb", "bbb"], False),
        ("three layers not match layer1 and miss 1 element and provide lots of other not match elements", "a and (b or (bb and bbb)) and c", ["a", "b", "bb", "bbb", "d"], False),
        ("three layers not match layer2 and", "a or (b and (bb or bbb)) or c", ["b"], False),

    ],
)
def test_slot_expression_check(test_name, expression, slot_names, expected):
    checker = ExpressionSlotSequenceChecker(expression)
    actual = checker.check_slot_missing(slot_names)
    assert actual == expected


# test missed slots for expression
# use exact same parametrize as above, only change the expected value

@pytest.mark.parametrize(
    "test_name, expression, slot_names, expected",
    [
        # one layer
        ("one layer exact match", "a and b and c", ["a", "b", "c"], [[]]),
        ("one layer match or any", "a or b or c", ["a"], [[], ["b"], ["c"]]),
        ("one layer match or any2", "a or b or c", ["b"], [[], ["a"], ["c"]]),
        ("one layer match or any3", "a or b or c", ["c"], [[], ["a"], ["b"]]),

        ("one layer not match with one missing", "a and b and c", ["a", "b"], [["c"]]),

        # two layers
        ("two layers exact match", "a and (b or bb) and c", ["a", "b", "bb", "c"], [[]]),
        ("two layers match each in layer2 or", "a and (b or bb) and c", ["a", "b", "c"], [[], ["bb"]]),
        ("two layers match each in layer2 or case2", "a and (b or bb) and c", ["a", "bb", "c"], [[], ["b"]]),
        ("two layers match all overflow", "a and (b or bb) and c", ["a", "b", "c", "d"], [[], ["bb"]]),
        ("two layers match layer1 or", "a or (b and bb) or c", ["a"], [[], ["b", "bb"], ["c"]]),
        ("two layers match layer1 or case2", "a or (b and bb) or c", ["b", "bb"], [[], ["a"], ["c"]]),
        ("two layers match layer1 or case3", "a or (b and bb) or c", ["c"], [[],["a"], ["b", "bb"]]),

        ("two layers not match miss one", "a and (b or bb) and c", ["a", "b"], [["c"], ["bb", "c"]]),
        ("two layers not match miss one case 2", "a and (b or bb) and c", ["a", "b", "bb"], [["c", "c"]]),
        ("two layers not match one different element", "a and (b or bb) and c", ["a", "bb", "d"], [["b", "c"], ["c"]]),
        ("two layers not match layer2 and", "a or (b and bb) or c", ["b"], [["a"], ["c"], ["bb"]]),

        # three layers
        ("three layers exact match", "a and (b or (bb and bbb)) and c", ["a", "b", "bb", "bbb", "c"], [[]]),
        ("three layers match only one element in layer2 or", "a and (b or (bb and bbb)) and c", ["a", "b", "c"], [[], ["bb", "bbb"]]),
        ("three layers match only one element in layer2 or case2", "a and (b or (bb and bbb)) and c", ["a", "b", "c", "d"], [[], ["bb", "bbb"]]),
        ("three layers match only one element in layer2 or|all in layer3 and", "a and (b or (bb and bbb)) and c", ["a", "bb", "bbb", "c"], [[], ["b"]]),
        ("three layers match layer1 or case1", "a or (b and (bb or bbb)) or c", ["a"], [[], ["b", "bb"], ["b", "bbb"], ["c"]]),
        ("three layers match layer1 or case2", "a or (b and (bb or bbb)) or c", ["c"], [[], ["a"], ["b", "bb"], ["b", "bbb"]]),
        ("three layers match only one element in layer1 or | layer2 and | layer3 or case1", "a or (b and (bb or bbb)) or c", ["b", "bb"], [[], ["a"], ["bbb"], ["c"]]),
        ("three layers match only one element in layer1 or | layer2 and | layer3 or case2", "a or (b and (bb or bbb)) or c", ["b", "bbb"], [[], ["a"], ["bb"], ["c"]]),
        ("three layers match only one element in layer1 or | layer2 and | layer3 or case3", "a or (b and (bb or bbb)) or c", ["b", "bb", "bbb"], [[], ["a"], ["c"]]),

        ("three layers not match layer1 and miss 1 element case1", "a and (b or (bb and bbb)) and c", ["a", "b"], [["c"], ["bb", "bbb", "c"]]),
        ("three layers not match layer1 and miss 1 element case2", "a and (b or (bb and bbb)) and c", ["a", "b", "bb"], [["c"], ["bbb", "c"]]),
        ("three layers not match layer1 and miss 1 element case3", "a and (b or (bb and bbb)) and c", ["a", "b", "bb", "bbb"], [["c"], ["c"]]),
        ("three layers not match layer1 and miss 1 element and provide lots of other not match elements", "a and (b or (bb and bbb)) and c", ["a", "b", "bb", "bbb", "d"], [["c"], ["c"]]),
        ("three layers not match layer2 and", "a or (b and (bb or bbb)) or c", ["b"], [["a"], ["bb"], ["c"], ["bbb"]]),
    ],
)
def test_slot_expression_check_missed_slots(test_name, expression, slot_names, expected):
    checker = ExpressionSlotSequenceChecker(expression)
    actual = checker.get_missed_slots(slot_names)
    for i in range(len(actual)):
        assert set(actual[i]) in [set(e) for e in expected]
