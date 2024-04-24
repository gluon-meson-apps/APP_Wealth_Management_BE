import asyncio
import json
import os
import uuid

import yaml

from nlu.llm.intent import topic
from resources.util import get_resources
from third_system.unified_search import UnifiedSearch

intent_yaml_file_folder = get_resources("scenes")
# unified_search_base_url = os.environ.get("UNIFIED_SEARCH_URL", "http://localhost:8000")
unified_search_base_url = "http://3.25.115.152:18001"


def retrieve_intent_examples_from_intent_yaml(folder_path, full_parent_intent=None):
    intent_examples = []

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        if os.path.isdir(item_path):
            # 如果是文件夹，则递归调用函数处理文件夹中的内容
            examples = retrieve_intent_examples_from_intent_yaml(item_path, item)
            intent_examples.extend(examples)
        elif item.endswith(".yaml"):
            # 如果是 YAML 文件，则读取其中的内容并处理
            with open(item_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
            if data and data.get("name"):
                intent_name = data.get("name")
                full_intent_name = f"{full_parent_intent}.{intent_name}" if full_parent_intent else intent_name

                # 提取意图示例并添加到列表中
                all_examples = data.get("examples", []) + data.get("display_examples", [])
                for example in all_examples:
                    intent_examples.append({
                        "intent": data["name"],
                        "example": example,
                        "full_parent_intent": full_intent_name,
                    })

    return intent_examples


def generate_tmp_example_file(intent_examples):
    file_name = f"intent_examples_{str(uuid.uuid4())}.txt"
    file_path = os.path.join("/tmp", file_name)
    with open(file_path, "w") as f:
        f.write(json.dumps(intent_examples))
    return file_name, file_path


async def vectorize_examples(intent_examples):
    unified_search_client = UnifiedSearch()

    response = await unified_search_client.upload_intents_examples(table=topic, intent_examples=intent_examples)

    return response


async def main():
    intent_examples = retrieve_intent_examples_from_intent_yaml(intent_yaml_file_folder)
    print(intent_examples)
    if len(intent_examples) == 0:
        print("No examples")
        return

    responses = await vectorize_examples(intent_examples)
    print(responses)


if __name__ == "__main__":
    asyncio.run(main())
