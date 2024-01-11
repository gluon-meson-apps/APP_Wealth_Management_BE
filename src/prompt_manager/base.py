import os

from loguru import logger

from prompt_manager.local_prompt_service import LocalPromptService
from utils.utils import format_jinja_template


class PromptWrapper:
    def __init__(self, template):
        self.template = template

    def format(self, values):
        formatted = self.template
        for key, value in values.items():
            formatted = formatted.replace("{{" + key + "}}", str(value))
        return formatted

    def format_jinja(self, **values):
        return format_jinja_template(self.template, **values)


class PromptManager:
    def load(self, name, domain=None) -> PromptWrapper:
        raise NotImplementedError()


class BasePromptManager(PromptManager):
    def __init__(self, prompt_template_folder=None) -> None:
        super().__init__()
        if prompt_template_folder is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_template_folder = os.path.join(current_dir, "..", "resources", "prompt_templates")
        self.prompt_service = LocalPromptService(prompt_template_folder)

    def load(self, name, domain=None) -> PromptWrapper:
        if domain is not None:
            name = domain + "_" + name

        prompt = self.prompt_service.get_prompt(name)
        if prompt is None:
            logger.warning(f"Prompt {name} not found")
            return None
        return PromptWrapper(prompt)
