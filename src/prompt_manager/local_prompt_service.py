import os


class LocalPromptService:

    def __init__(self, prompt_template_folder):
        self.prompt_template_folder = prompt_template_folder

    def get_prompt(self, name) -> str:
        prompt_file_path = os.path.join(self.prompt_template_folder, name + ".txt")
        if os.path.isfile(prompt_file_path):
            with open(prompt_file_path, 'r', encoding='utf-8') as file:
                return file.read()
        return None
