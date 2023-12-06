import unittest
from output_adapter.base import BaseOutputAdapter

class TestNormalizePercentage(unittest.TestCase):
    def setUp(self):
        self.test_cases = {
            "26%": "26%",
            "百分之28": "28%",
            "百分之二十八": "28%",
            "%23": "23%",
            "百分之110": "110%",
            "120%": "120%",
            "random text": ""  # 用于触发警告的测试用例
        }
        self.adapter = BaseOutputAdapter()

    def test_normalize_percentage(self):
        for input_text, expected_output in self.test_cases.items():
            result = self.adapter.normalize_percentage(input_text)
            self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()
