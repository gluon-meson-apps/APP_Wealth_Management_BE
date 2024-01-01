import yaml

import os


def load_secret(name, cls):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(f'{dir_path}/{name}', "r", encoding="utf-8") as file:
        file_dict = yaml.safe_load(file)
        return cls(**file_dict)
