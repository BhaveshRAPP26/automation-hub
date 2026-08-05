from datetime import datetime
from pathlib import Path
import json
import os

####################################################
# Timestamp
####################################################

def timestamp():

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


####################################################
# Filename timestamp
####################################################

def filename_timestamp():

    return datetime.now().strftime("%Y%m%d_%H%M%S")


####################################################
# Ensure folder exists
####################################################

def ensure_directory(path):

    Path(path).mkdir(parents=True, exist_ok=True)


####################################################
# Save JSON
####################################################

def save_json(data, path):

    with open(path, "w", encoding="utf-8") as f:

        json.dump(data, f, indent=4)


####################################################
# Save text
####################################################

def save_text(text, path):

    with open(path, "w", encoding="utf-8") as f:

        f.write(text)


####################################################
# Safe value
####################################################

def safe(value):

    if value is None:

        return ""

    return str(value)


####################################################
# PASS / FAIL helper
####################################################

def status(condition):

    return "PASS" if condition else "FAIL"


####################################################
# Flatten dict
####################################################

def flatten(dictionary):

    result = {}

    for key, value in dictionary.items():

        if isinstance(value, dict):

            for k, v in value.items():

                result[f"{key}.{k}"] = v

        else:

            result[key] = value

    return result


####################################################
# Console logger
####################################################

def log(message):

    print(f"[{timestamp()}] {message}")