import json
from typing import List, Generator

import openai
import requests
from pydantic import BaseModel
from tenacity import retry, wait_random_exponential, stop_after_attempt

from gm_secrets.secret import load_secret

GPT_MODEL = "gpt-4"


class OpenAIChatModelConfig(BaseModel):
    openai_api_key: str


class OpenAIModel:
    def __init__(self,
                 model,
                 config: OpenAIChatModelConfig = load_secret("openai.yml", OpenAIChatModelConfig),
                 # cache: Union[cache, None] = None,
                 ) -> None:
        # self.logging.debug("init azure_openai model")
        # self.cache = cache
        openai.api_key = config.openai_api_key
        self.model = model

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def chat_completion_request(self, messages, tools=None, tool_choice=None):
        model = self.model
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + openai.api_key,
        }
        json_data = {"model": model, "messages": messages}
        if tools is not None:
            json_data.update({"tools": tools})
        if tool_choice is not None:
            json_data.update({"tool_choice": tool_choice})
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=json_data,
            )
            return response
        except Exception as e:
            print("Unable to generate ChatCompletion response")
            print(f"Exception: {e}")
            return e

    def chat_call(self, messages: List) -> str:
        chat_response = self.chat_completion_request(messages)
        print(chat_response.text)
        return chat_response.json()["choices"][0]["message"]['content']

    def chat(self,
             messages: List,
             model_type: str,
             use_cache=False,
             exact_match: bool = False,
             stream=False) -> str:
        if use_cache:
            response = self.cache.search_cache(messages, exact_match)
            if response:
                yield response
                return

        # self.logging.info("Calling OpenAI...")
        response = self.chat_call(messages, model_type, stream=stream)
        if isinstance(response, Generator):
            response_message = ""
            for chunk in response:
                if chunk["choices"] and len(chunk["choices"]) > 0:
                    if "content" in chunk["choices"][0]["delta"]:
                        yield json.loads(
                            json.dumps(chunk["choices"][0]["delta"]["content"])
                        )
                        response_message += chunk["choices"][0]["delta"]["content"]
            # Only add to cache when llm has valid output
        else:
            yield response
            response_message = response

        if use_cache:
            self.cache.add_cache(messages, response_message)

    def function_call(self,
                      messages: List,
                      functions: List,
                      model_type: str,
                      function_call="auto"):
        # self.logging.debug("Calling function_call")
        response = openai.ChatCompletion.create(
            deployment_id=model_type,
            messages=messages,
            functions=functions,
            function_call=function_call
        )
        try:
            return json.loads(json.dumps(response["choices"][0]["message"]))
        except Exception as e:
            # self.logging.error(str(e))
            return {"error": f"LLM Error: {e}"}
