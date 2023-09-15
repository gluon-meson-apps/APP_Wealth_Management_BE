from gluon_meson_sdk.prompt.prompt_service import PromptService

GLUON_MESON_MASTER_ENDPOINT = "http://10.207.227.101:18000" 

class PromptWrapper:
    def __init__(self, template):
        self.template = template
        
    def format(self, values):
        formatted = self.template
        for key, value in values.items():
            formatted = formatted.replace("{{" + key + "}}", str(value))
        return formatted
    
class PromptManager:
    def load(self, domain, style) -> str:
        raise NotImplementedError()

class BasePromptManager(PromptManager):
    
    def __init__(self) -> None:
        super().__init__()
        self.prompt_service = PromptService(master_endpoint=GLUON_MESON_MASTER_ENDPOINT)
    
    def load(self, domain, style=None) -> str:
        if style is not None:
            name = domain + '_' + style
        else:
            name = domain
        prompt = self.prompt_service.get_prompt(name)
        if prompt is None:
            if domain == "slot_filling":
                prompt = """你是一个友好的智能机器人，在==聊天历史开始==和==聊天历史结束==之间的你和用户之间的对话，用户的目的是{{intent}}，但是他没有提供{{fill_slot}}的信息，请对用户进行引导，让他提供所缺失的信息
==聊天历史开始==
{{history}}
==聊天历史结束==
"""
            if domain == "response":
                prompt = "你是一个友好智能机器人，请对用户的问题\"{{input}}\"进行回复"
        return PromptWrapper(prompt)
