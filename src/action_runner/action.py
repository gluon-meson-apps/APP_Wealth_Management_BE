
from abc import ABC, abstractmethod
from gluon_meson_sdk.models.chat_model import ChatModel
from action_runner.context import ActionContext
from prompt_manager.base import PromptManager

class Action(ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def run(self, context: ActionContext): 
        pass
        
class ChatAction(Action):

    def __init__(self, style, model_name):
        self.prompt_template = PromptManager.load(domain='response', style=style)
        self.model = model_name
        self.llm = ChatModel(master_endpoint="http://localhost:8000/api/v1/chat")

    def name(self):
        return "chat"

    def run(self, context):
        user_input = context.get_user_input()
        prompt = self.prompt_template.format(user_input)
        response = self.llm.chat_single(prompt, model_type=self.model)
        return response
        
class SlotFillingAction(Action):

    def __init__(self, style, model_name):
        self.prompt_template = PromptManager.load(domain='slot_filling', style=style)
        self.model = model_name
        self.llm = ChatModel(master_endpoint="http://localhost:8000/api/v1/chat")

    def name(self):
        return "slot_filling"

    def run(self, context):
        slots = context.get_slots()
        user_input = context.get_user_input()
        prompt = self.prompt_template.format(user_input, **slots)
        response = self.llm.chat_single(prompt, model_type=self.model)
        return response

class FixedAnswerAction(Action):
    
    PresetResponses = {
        "评价": "谢谢您的评价，我们会不断改进，谢谢！",
        "感谢": "谢谢您的评价，我们会不断改进，谢谢！",
        "打招呼": "您好，请问有什么可以帮助您的吗？",
        "结束语": "再见，祝您生活愉快！",
    }

    def __init__(self, response_policy):
        self.response = self.PresetResponses.get(response_policy)

    def name(self):
        return "fixed_answer"

    def run(self):
        return self.response