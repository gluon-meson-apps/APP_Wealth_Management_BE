import unittest

from parameterized import parameterized

from output_adapter.base import BaseOutputAdapter

input_and_expected_value = [
    [
        '百分之50',
        '0.5',
    ],
    [
        '百分之五十',
        '0.5',
    ],
    [
        '50%',
        '0.5',
    ],
    [
        '倒数第二列',
        '-2',
    ],
    [
        '第三列',
        '3',
    ],
    [
        '倒数三',
        '-3',
    ],
    [
        '倒数3',
        '-3',
    ],
]


class TestNormalizePercentage(unittest.TestCase):
    @parameterized.expand(input_and_expected_value)
    def test_single_chat_intent_and_slots(self, input, expected_value):
        adapter = BaseOutputAdapter()
        result = adapter.normalize_slot_value(input)
        assert result == expected_value


if __name__ == '__main__':
    unittest.main()
