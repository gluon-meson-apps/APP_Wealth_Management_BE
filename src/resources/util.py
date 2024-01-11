import os


def get_resources(path: str):
    current_script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_script_dir, path)
