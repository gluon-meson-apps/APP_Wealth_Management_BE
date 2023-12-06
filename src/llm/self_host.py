import json
import configparser
import os

from colorama import init, Fore
from loguru import logger
from openai import OpenAI

from util import dispatch_tool

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../', 'config.ini'))

base_url = config['LLM']['base_url']

init(autoreset=True)
# client = OpenAI(
#     base_url = base_url,
#     api_key = "xxx"
# )
# model = "chatglm3"

client = OpenAI(
    api_key = "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"
)

model = "gpt-3.5-turbo"

class ChatModel():
    def chat(self, query, stream=False, history=[], functions=None, max_retry=5, max_length=256, temperature=0.0):
        params = dict(model=model, messages=[{"role": "user", "content": query}] + history, stream=stream)
        params["max_tokens"] = max_length
        params["temperature"] = temperature
        
        if functions:
            params["functions"] = functions
        print(params)
        response = client.chat.completions.create(**params)

        for _ in range(max_retry):
            if not stream:
                if response.choices[0].message.function_call:
                    function_call = response.choices[0].message.function_call
                    logger.info(f"Function Call Response: {function_call.model_dump()}")

                    function_args = json.loads(function_call.arguments)
                    tool_response = dispatch_tool(function_call.name, function_args)
                    logger.info(f"Tool Call Response: {tool_response}")

                    params["messages"].append(response.choices[0].message)
                    params["messages"].append(
                        {
                            "role": "function",
                            "name": function_call.name,
                            "content": tool_response,  # 调用函数返回结果
                        }
                    )
                else:
                    reply = response.choices[0].message.content
                    return reply

            else:
                output = ""
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    print(Fore.BLUE + content, end="", flush=True)
                    output += content

                    if chunk.choices[0].finish_reason == "stop":
                        print("\n")
                        return output

                    elif chunk.choices[0].finish_reason == "function_call":
                        print("\n")

                        function_call = chunk.choices[0].delta.function_call
                        logger.info(f"Function Call Response: {function_call.model_dump()}")

                        function_args = json.loads(function_call.arguments)
                        tool_response = dispatch_tool(function_call.name, function_args)
                        logger.info(f"Tool Call Response: {tool_response}")

                        params["messages"].append(
                            {
                                "role": "assistant",
                                "content": output
                            }
                        )
                        params["messages"].append(
                            {
                                "role": "function",
                                "name": function_call.name,
                                "content": tool_response,  # 调用函数返回结果
                            }
                        )

                        break

            response = client.chat.completions.create(**params)