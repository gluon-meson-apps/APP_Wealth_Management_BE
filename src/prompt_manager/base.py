class PromptManager:
    def load(self, output: str) -> str:
        raise NotImplementedError()


class BasePromptManager(PromptManager):
    def load(self, domain, style) -> str:
        if domain == 'response':
            return f'以{style}的风格对下面的内容进行回复'
