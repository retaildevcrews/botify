import json
import time


def load_jsonl(path):
    with open(path, "r") as f:
        return [json.loads(line) for line in f.readlines()]


def get_output_file_name(filename: str):
    datestring = time.time()
    filename = f"{filename}_{datestring}.jsonl"
    return
