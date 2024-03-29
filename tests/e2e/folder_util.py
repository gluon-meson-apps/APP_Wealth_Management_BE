import os

rootdir = '/Users/rlin/tw-project/2023/ai_platform/chatbot/thought-agent/tests/e2e/generated/batch_qa_1'


def folder_to_dict(root_folder):
    dict_tree = {}
    for root, dirs, files in os.walk(root_folder):
        path = root.split(os.sep)
        sub_folder = root[len(root_folder) + 1:]
        sub_folder_splits = sub_folder.split(os.sep)

        dict_tree_tmp = dict_tree
        for item in sub_folder_splits:
            if item not in dict_tree_tmp:
                dict_tree_tmp[item] = {}
            dict_tree_tmp = dict_tree_tmp[item]

        for file in files:
            dict_tree_tmp[file] = file
    return dict_tree


def convert_folder_dict_list_like(dict_tree, prefix=""):
    current_layer_folders = []
    for key, value in dict_tree.items():
        if key in ('tmp', "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode"):
            continue
        if isinstance(value, dict):
            current_layer_folders.append({
                "label": key,
                "value": prefix+'/'+key,
                "children": convert_folder_dict_list_like(value, prefix+'/'+key)
            })
        else:
            current_layer_folders.append({"label": key, "value": prefix+'/'+key})
    return sorted(current_layer_folders, key=lambda x: x['label'])


if __name__ == '__main__':
    print(folder_to_dict(rootdir))
    print(convert_folder_dict_list_like(folder_to_dict(rootdir)))
