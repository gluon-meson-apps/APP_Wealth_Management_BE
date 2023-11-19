import unittest

from action_runner.action import ChatAction, SlotFillingAction, FixedAnswerAction
from action_runner.base import BaseActionRunner
from action_runner.context import ActionContext

GLUON_MESON_CONTROL_CENTER_ENDPOINT = "http://10.207.227.101:18000"

class TestActionRunner(unittest.TestCase):

    def setUp(self):
        default_model = "azure-gpt-3.5"
        self.context = ActionContext()
        self.context.set_user_input("Hello")
        self.context.set_slot("name", None)
        
        self.runner = BaseActionRunner()
        
        self.chat_action = ChatAction("friendly", default_model)
        self.slot_action = SlotFillingAction(default_model)
        self.fixed_action = FixedAnswerAction("打招呼")
        
        self.runner.register_actions("chat", self.chat_action)
        self.runner.register_actions("slot", self.slot_action)
        self.runner.register_actions("fixed", self.fixed_action)

    def test_chat_action(self):
        response = self.runner.run("chat", self.context)
        self.assertTrue(len(response) > 0) 

    def test_slot_filling_action(self):  
        response = self.runner.run("slot", self.context)
        self.assertTrue(len(response) > 0) 

    def test_fixed_action(self):
        response = self.runner.run("fixed", self.context)
        self.assertEqual(response, "您好,请问有什么可以帮助您的吗?")

if __name__ == '__main__':
    unittest.main()