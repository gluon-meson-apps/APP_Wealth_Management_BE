import json
import os
import uuid

import yaml

from unified_search_client.unified_search_client import UnifiedSearchClient

intent_yaml_file_folder = os.path.join(os.getcwd(), "src", "resources", "scenes")
unified_search_base_url = os.environ.get("UNIFIED_SEARCH_URL", "http://localhost:8000")

def retrieve_intent_examples_from_intent_yaml(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith(".yaml")]

    intent_examples = []
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if "examples" in data:
            intent_examples.append({
                "intent": data.get("name"),
                "examples": data.get("examples")
            })

    return intent_examples

def generate_tmp_example_file(intent_examples):
    file_name = f"intent_examples_{str(uuid.uuid4())}.txt"
    file_path = os.path.join("/tmp", file_name)
    with open(file_path, "w") as f:
        f.write(json.dumps(intent_examples))
    return file_name, file_path

def vectorize_examples(intent_examples):
    unified_search_client = UnifiedSearchClient(unified_search_base_url)

    tmp_file_name, tmp_file_path = generate_tmp_example_file(intent_examples)
    f = open(tmp_file_path, "r")
    files = [("files", (tmp_file_name, f, "text/plain"))]

    data = {
        "tag": "new_tag"
    }
    response = unified_search_client.post_files_and_tag(
        path="/vector/embedding",
        files=files,
        data=data,
    )
    f.close()
    os.remove(tmp_file_path)
    return response

def main():
    intent_examples = retrieve_intent_examples_from_intent_yaml(intent_yaml_file_folder)

    if len(intent_examples) == 0:
        print("No examples")
        return

    response = vectorize_examples(intent_examples)
    print(response.status_code, response.text)

if __name__ == "__main__":
    main()