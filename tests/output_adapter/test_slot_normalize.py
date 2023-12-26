import unittest

from parameterized import parameterized

from output_adapter.base import BaseOutputAdapter, NormalizeType

input_and_expected_value = [
    [
        '百分之5',
        'font_change',
        '10',
    ],
    [
        '百分之4',
        'font_change',
        '10',
    ],
    [
        '百分之15',
        'font_change',
        '20',
    ],
    [
        '百分之14',
        'font_change',
        '20',
    ],
    [
        '百分之五',
        'font_change',
        '10',
    ],
    [
        '5%',
        'font_change',
        '10',
    ],
    [
        '倒数第二列',
        'header_position',
        '-2',
    ],
    [
        '第三列',
        'header_position',
        '3',
    ],
    [
        '倒数三',
        'header_position',
        '-3',
    ],
    [
        '倒数3',
        'header_position',
        '-3',
    ],
    [
        '月消费',
        'header_position',
        '月消费'
    ]
]


class TestNormalizePercentage(unittest.TestCase):
    @parameterized.expand(input_and_expected_value)
    def test_normalize_slot_value(self, input, normalize_type, expected_value):
        adapter = BaseOutputAdapter()
        result = adapter.normalize_slot_value(input, normalize_type, "test_normalize")
        assert result == expected_value


if __name__ == '__main__':
    unittest.main()
