import unittest
from output_adapter.base import BaseOutputAdapter

class TestNormalizePercentage(unittest.TestCase):
    def setUp(self):
        self.test_cases = {
            "20%": "20%",
            "百分之20": "20%",
            "百分之二十": "20%",
            "%20": "20%",
            "random text": ""  # 用于触发警告的测试用例
        }
        self.adapter = BaseOutputAdapter()

    def test_normalize_percentage(self):
        for input_text, expected_output in self.test_cases.items():
            result = self.adapter.normalize_percentage(input_text)
            self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()
