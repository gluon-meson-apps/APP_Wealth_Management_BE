import unittest

from parameterized import parameterized

from output_adapter.base import BaseOutputAdapter, NormalizeType

input_and_expected_value = [
    [
        '百分之5',
        NormalizeType.PERCENTAGE,
        '10',
    ],
    [
        '百分之4',
        NormalizeType.PERCENTAGE,
        '10',
    ],
    [
        '百分之15',
        NormalizeType.PERCENTAGE,
        '20',
    ],
    [
        '百分之14',
        NormalizeType.PERCENTAGE,
        '20',
    ],
    [
        '百分之五',
        NormalizeType.PERCENTAGE,
        '10',
    ],
    [
        '5%',
        NormalizeType.PERCENTAGE,
        '10',
    ],
    [
        '倒数第二列',
        NormalizeType.NUMBER,
        '-2',
    ],
    [
        '第三列',
        NormalizeType.NUMBER,
        '3',
    ],
    [
        '倒数三',
        NormalizeType.NUMBER,
        '-3',
    ],
    [
        '倒数3',
        NormalizeType.NUMBER,
        '-3',
    ],
    [
        '月消费',
        NormalizeType.STRING,
        '月消费'
    ]
]


class TestNormalizePercentage(unittest.TestCase):
    @parameterized.expand(input_and_expected_value)
    def test_normalize_slot_value(self, input, normalize_type, expected_value):
        adapter = BaseOutputAdapter()
        result = adapter.normalize_slot_value(input, normalize_type)
        assert result == expected_value


if __name__ == '__main__':
    unittest.main()
