import json
import os.path
from pathlib import Path


def create_directories_if_not(filepath: str):
    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)


def delete_all(paths: list[str]):
    for path in paths:
        os.remove(path)


def try_read_json_array(path: str):
    if not os.path.exists(path):
        return None

    with open(path, "r") as fin:
        data = json.load(fin)

    if not isinstance(data, list):
        return None

    return data


def write_json_array(array: list, path: str):
    create_directories_if_not(path)
    with open(path, "w") as fout:
        print(json.dumps(array), file=fout)
