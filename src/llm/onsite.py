import configparser
import os
import requests

from fastapi import HTTPException

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../', 'config.ini'))

base_url = config['LLM']['base_url']
model = config['LLM']['model']

class ChatModel():
    def __init__(self):
        if model == 'chatglm3_6b':
            self.chat = self._chat_model_A
        elif model == 'cpm_80b' or model == 'llama_70b':
            self.chat = self._chat_model_B
        else:
            raise ValueError("Invalid model type")

    def _chat_model_A(self, query, stream=False, history=[], functions=None, max_retry=5, max_length=128, temperature=0.0):
        params = dict(messages=[{"role": "user", "content": query}])
        params["max_length"] = max_length
        params["temperature"] = temperature + 0.01
        params["stop"] = ["\n"]
        response = requests.post(base_url, json=params)

        if response.status_code == 200:
            reply = response.json().get("choices")[0].get("message").get("content")
            return reply.replace('\n ', '', 1)
        else:
            raise HTTPException(
                status_code=response.status_code, detail={response.text}
            )

    def _chat_model_B(query, stream=False, history=[], functions=None, max_retry=5, max_length=128, temperature=0.0):
        payload = {
            "inputs": f"用户：{query} <sep>AI：",
            "parameters": {
                "do_sample": True,
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 80,
                "max_new_tokens": max_length,
                "return_full_text": False
            }
        }

        response = requests.post(base_url, json=payload)

        if response.status_code == 200:
            # Process the response here if needed
            return response.json()  # Modify as per your response structure
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text  # Adjust the response handling as needed
            )
