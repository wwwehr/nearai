from datetime import datetime as dt
from pathlib import Path

from jasnah.config import CONFIG
from jasnah.db import db


def timestamp() -> str:
    return dt.now().strftime("%Y%m%d%H%M%S%f")


def cli_path() -> Path:
    return Path(__file__).parent.parent


def etc(file: str) -> Path:
    return cli_path() / "etc" / file


def get_origin():
    if CONFIG.origin:
        return CONFIG.origin

    if CONFIG.user_name:
        return CONFIG.user_name

    CONFIG.origin = f"anonymous_{timestamp()}"
    return CONFIG.origin


def log(content):
    origin = get_origin()
    db.log(origin, content)
