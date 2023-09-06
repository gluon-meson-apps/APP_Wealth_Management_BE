from gluon_meson_sdk.prompt.prompt_service import PromptService

class PromptManager:
    def load(self, output: str) -> str:
        raise NotImplementedError()


class BasePromptManager(PromptManager):
    
    def __init__(self) -> None:
        super().__init__()
        self.prompt_service = PromptService()
    
    def load(self, domain, style) -> str:
        name = domain + '_' + style
        prompt = self.prompt_service.get_prompt(name)
        return prompt
