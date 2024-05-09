from pathlib import Path


def cli_path() -> Path:
    return Path(__file__).parent.parent


def etc(file: str) -> Path:
    return cli_path() / "etc" / file
