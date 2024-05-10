import json
from pathlib import Path
from typing import Any, Dict

DATA_FOLDER = Path.home() / ".jasnah"
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_FOLDER / "config.json"


def load_config_file() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE) as f:
        config = json.load(f)
    return config


def save_config_file(config: Dict[str, Any]):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def update_config(key, value):
    config = load_config_file()
    config[key] = value
    save_config_file(config)


CONFIG = load_config_file()

S3_BUCKET = CONFIG.get("s3_bucket", "kholinar-datasets")
S3_PREFIX = CONFIG.get("s3_prefix", "registry")
SUPERVISORS = CONFIG.get("supervisors", [])
