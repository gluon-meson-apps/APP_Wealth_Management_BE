import asyncio
import json
import os
import uuid

import yaml

from nlu.llm.intent import topic
from resources.util import get_resources
from third_system.unified_search import UnifiedSearch

intent_yaml_file_folder = get_resources("scenes")
unified_search_base_url = os.environ.get("UNIFIED_SEARCH_URL", "http://localhost:8000")


def retrieve_intent_examples_from_intent_yaml(folder_path, full_parent_intent=None):
    files = [f for f in os.listdir(folder_path) if f.endswith(".yaml")]

    intent_examples = []
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        if data and data.get("name"):
            intent_name = data.get("name")
            if data.get("has_children"):
                full_parent = f"{full_parent_intent}.{intent_name}" if full_parent_intent else intent_name
                examples = retrieve_intent_examples_from_intent_yaml(f"{folder_path}/{intent_name}", full_parent)
                intent_examples.extend(examples)

            all_examples = data.get("examples", []) + data.get("display_examples", [])

            for example in all_examples:
                intent_examples.append(
                    {
                        "intent": data["name"],
                        "example": example,
                        "full_parent_intent": full_parent_intent,
                    }
                )

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

    if len(intent_examples) == 0:
        print("No examples")
        return

    responses = await vectorize_examples(intent_examples)
    print(responses)


if __name__ == "__main__":
    asyncio.run(main())
