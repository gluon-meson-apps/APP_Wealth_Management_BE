import configparser
import os

from colorama import init
from openai import OpenAI

from gluon_meson_sdk.models.chat_model import ChatModel as GMChatModel

from llm.openai_model import OpenAIModel

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "../", "config.ini"))

base_url = config["LLM"]["base_url"]

init(autoreset=True)
client = OpenAI(base_url=base_url, api_key="xxx")
model = "chatglm3"


# client = OpenAI(
#     api_key = "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"
# )

# model = "gpt-3.5-turbo"


class ChatModel:
    def __init__(self):
        self.model = GMChatModel()

    def chat(
            self,
            query,
            stream=False,
            history=[],
            functions=None,
            max_retry=5,
            max_length=128,
            temperature=0.0,
            model_type=None,
    ):
        if history and "role" not in history[0]:
            history = [
                {
                    "role": h[0],
                    "content": h[1]
                }
                for h in history
            ]
        return OpenAIModel("gpt-3.5-turbo").chat_call(
            history + [{"role": "user", "content": query}],
        )
        # return self.model.chat_single(
        #     query,
        #     model_type=model_type,
        #     history=history,
        #     max_length=max_length,
        #     temperature=temperature,
        # ).response
