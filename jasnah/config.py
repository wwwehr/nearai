import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_FOLDER = Path.home() / ".jasnah"
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_FOLDER / "config.json"
LOCAL_CONFIG_FILE = Path(".jasnah") / "config.json"


def get_config_path(local: bool = False) -> Path:
    return LOCAL_CONFIG_FILE if local else CONFIG_FILE


def load_config_file(local: bool = False) -> Dict[str, Any]:
    path = get_config_path(local)

    if not path.exists():
        return {}

    with open(path) as f:
        config = json.load(f)
    return config


def save_config_file(config: Dict[str, Any], local: bool = False):
    path = get_config_path(local)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(config, f, indent=4)


def update_config(key, value, local=False):
    config = load_config_file(local)
    config[key] = value
    save_config_file(config, local)


@dataclass
class Config:
    s3_bucket: str = "kholinar-datasets"
    s3_prefix: str = "registry"
    supervisors: List[str] = field(default_factory=list)
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: str = "35.87.119.37"
    db_port: int = 3306
    db_name: str = "marx_test"
    server_url: str = "http://10.141.0.11:8100"
    origin: str = None
    user_name: str = None
    user_email: str = None
    supervisor_id: str = None

    def update_with(self, extra_config: Dict[str, Any], map_key=lambda x: x):
        keys = [f.name for f in fields(self)]
        for key in map(map_key, keys):
            value = extra_config.get(key, None)

            if value:
                # This will skip empty values, even if they are set in the `extra_config`
                setattr(self, key, extra_config[key])


# Load default configs
CONFIG = Config()
# Update config from global config file
CONFIG.update_with(load_config_file(local=False))
# Update config from local config file
CONFIG.update_with(load_config_file(local=True))
# Update config from environment variables
CONFIG.update_with(os.environ, map_key=str.upper)
