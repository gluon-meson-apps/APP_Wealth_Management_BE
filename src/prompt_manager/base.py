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
                prompt = "请引导用户对{{fill_slot}}填充"
            if domain == "response":
                prompt = "你是一个友好智能机器人，请对用户的问题\"{{input}}\"进行回复"
        return PromptWrapper(prompt)
