from typing import Sequence

import pytest

from policy.slot_filling.slot_sequence_checker import OneSlotSequenceChecker, MultiSlotSequenceChecker


@pytest.mark.parametrize(
    "comment, sequence, real_slots, expected",
    [
        ('match_empty_slots', [], ["a"], True),
        ('exact_match', ["a", "b", "c"], ["a", "b", "c"], True),
        ('match_overflow', ["a", "b"], ["a", "b", "c"], True),
        ('match_with_mess_order', ["a", "b"], ["b", "a", "c"], True),

        ('not_match_with_empty_elements', ["a"], [], False),
        ('not_match_with_different_elements', ["d", "e"], ["a", "b", "c"], False),
        ('not_match_with_only_one_different_element', ["a", "b", "d"], ["a", "b", "c"], False),
        ('not_match_with_only_one_absent_element', ["a", "b", "c", "d"], ["a", "b", "c"], False),
        ('not_match_with_multiple_absent_elements', ["a", "b", "c", "d", "e"], ["a", "b", "c"], False),
    ],
)
def test_one_slot_sequence_checker(comment, sequence: Sequence[str], real_slots, expected: bool):
    checker = OneSlotSequenceChecker(sequence)
    actual = checker.check_slot_missing(real_slots)
    assert actual == expected

@pytest.mark.parametrize(
    "comment, sequence, real_slots, expected",
    [
        ("match_one_empty_slots_with_empty_elements", [[], ["c", "d"]], [], True),
        ("match_one_empty_slots_with_some_elements", [[], ["c", "d"]], ["e"], True),
        ("all_match", [["a", "b"], ["c", "d"]], ["a", "b", "c", "d"], True),
        ("match_one_sequence", [["a", "b"], ["c", "d"]], ["a", "b", "c"], True),
        ("all_match_overflow", [["a", "b"], ["c", "d"]], ["a", "b", "c", "d", "e"], True),
        ("match_with_reverse_order", [["a", "b"], ["c", "d"]], ["b", "a", "d", "c"], True),

        ("not_match_with_empty", [["a", "b"], ["c", "d"]], [], False),
        ("not_match_with_each_sequence_only_match_partial", [["a", "b"], ["c", "d"]], ["a", "d"], False),
        ("not_match_with_different_elements", [["a", "b"], ["c", "d"]], ["x", "y", "z"], False),
]
)
def test_multiple_slot_sequence_checker(comment, sequence: Sequence[Sequence[str]], real_slots, expected: bool):
    checker = MultiSlotSequenceChecker(sequence)
    actual = checker.check_slot_missing(real_slots)
    assert actual == expected


# test missed slots

@pytest.mark.parametrize(
    "comment, sequence, real_slots, expected",
    [
        ('match_empty_slots', [], ["a"], []),
        ('exact_match', ["a", "b", "c"], ["a", "b", "c"], []),
        ('match_overflow', ["a", "b"], ["a", "b", "c"], []),
        ('match_with_mess_order', ["a", "b"], ["b", "a", "c"], []),

        ('not_match_with_empty_elements', ["a"], [], ["a"]),
        ('not_match_with_different_elements', ["d", "e"], ["a", "b", "c"], ["d", "e"]),
        ('not_match_with_only_one_different_element', ["a", "b", "d"], ["a", "b", "c"], ["d"]),
        ('not_match_with_only_one_absent_element', ["a", "b", "c", "d"], ["a", "b", "c"], ["d"]),
        ('not_match_with_multiple_absent_elements', ["a", "b", "c", "d", "e"], ["a", "b", "c"], ["d", "e"]),
    ],
)
def test_one_slot_sequence_checker_get_missed_slots(comment, sequence: Sequence[str], real_slots, expected: Sequence[str]):
    checker = OneSlotSequenceChecker(sequence)
    actual = checker.get_missed_slots(real_slots)[0]
    assert set(actual) == set(expected)

# test missed slots for multiple slot sequence checker

@pytest.mark.parametrize(
    "comment, sequence, real_slots, expected",
    [
        ("match_one_empty_slots_with_empty_elements", [[], ["c", "d"]], [], [[]]),
        ("match_one_empty_slots_with_some_elements", [[], ["c", "d"]], ["e"], [[]]),
        ("all_match", [["a", "b"], ["c", "d"]], ["a", "b", "c", "d"], [[]]),
        ("match_one_sequence", [["a", "b"], ["c", "d"]], ["a", "b", "c"], [[]]),
        ("all_match_overflow", [["a", "b"], ["c", "d"]], ["a", "b", "c", "d", "e"], [[]]),
        ("match_with_reverse_order", [["a", "b"], ["c", "d"]], ["b", "a", "d", "c"], [[]]),

        ("not_match_with_empty", [["a", "b"], ["c", "d"]], [], [["a", "b"], ["c", "d"]]),
        ("not_match_with_each_sequence_only_match_partial", [["a", "b"], ["c", "d"]], ["a", "d"], [["b"], ["c"]]),
        ("not_match_with_each_sequence_only_match_partial_and_same_slot_in_diff_seq", [["a", "b"], ["a", "c", "d"]], ["a", "d"], [["b"], ["c"]]),
        ("not_match_with_different_elements", [["a", "b"], ["c", "d"]], ["x", "y", "z"], [["a", "b"], ["c", "d"]]),
    ]
)
def test_multiple_slot_sequence_checker_get_missed_slots(comment, sequence: Sequence[Sequence[str]], real_slots, expected: Sequence[Sequence[str]]):
    checker = MultiSlotSequenceChecker(sequence)
    actual = checker.get_missed_slots(real_slots)
    for a, e in zip(actual, expected):
        assert set(a) == set(e)
