from prompt_manager.local_prompt_service import LocalPromptService


class PromptWrapper:
    def __init__(self, template):
        self.template = template

    def format(self, values):
        formatted = self.template
        for key, value in values.items():
            formatted = formatted.replace("{{" + key + "}}", str(value))
        return formatted


class PromptManager:
    def load(self, name, domain) -> str:
        raise NotImplementedError()


class BasePromptManager(PromptManager):
    def __init__(self, prompt_template_folder) -> None:
        super().__init__()
        self.prompt_service = LocalPromptService(prompt_template_folder)

    def load(self, name, domain=None) -> PromptWrapper:
        if domain is not None:
            name = domain + "_" + name

        prompt = self.prompt_service.get_prompt(name)
        if prompt is None:
            return None
        return PromptWrapper(prompt)
