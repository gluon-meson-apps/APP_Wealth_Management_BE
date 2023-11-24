import unittest
import yaml
from src.nlu.llm.intent import IntentListConfig, IntentConfig
import os


class TestIntentListConfig(unittest.TestCase):

    def test_intent_list_config_from_yaml_file(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(pwd, '..', '..', 'resources', 'intent.yaml')
        intent_list_config = IntentListConfig.from_scenes(file_path)
        
        self.assertIsInstance(intent_list_config, IntentListConfig)

        # Check that intent_config has the correct number of intents
        self.assertEqual(len(intent_list_config.intents), 4)

        # Check the details of the first intent
        first_intent = intent_list_config.intents[0]
        self.assertEqual(first_intent.name, '控制智能家居')
        self.assertEqual(first_intent.examples, ['帮忙打开卧室的空调', '关灯', '打开电视', '关闭窗帘'])
        self.assertEqual(list(map(lambda s: s['name'], first_intent.slots)), ['位置', '操作', '对象', '操作值'])

        # Check the details of the second intent
        second_intent = intent_list_config.intents[1]
        self.assertEqual(second_intent.name, '设置闹钟')
        self.assertEqual(second_intent.examples, ['明天早上六点叫我起床', '提醒我下午三点开会', '明天早上八点半叫我起床'])
        self.assertEqual(list(map(lambda s: s['name'], second_intent.slots)), ['日期', '时间', '事件'])

    def test_get_intent_list(self):
        pwd = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(pwd, '..', '..', 'resources', 'intent.yaml')
        print(file_path)
        intent_list_config = IntentListConfig.from_scenes(file_path)

        intent_list = intent_list_config.get_intent_list()

        intent_and_examples = intent_list_config.get_intent_and_examples()

        self.assertEqual(intent_list, ['控制智能家居', '设置闹钟', '查询天气', '查看日程'])
        self.assertEqual(intent_and_examples[0], {'intent': '控制智能家居', 'examples': ['帮忙打开卧室的空调', '关灯', '打开电视', '关闭窗帘']})

if __name__ == '__main__':
    unittest.main()
