import json
import os
import runpy
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from nearai.lib import _check_metadata
from nearai.registry import get_registry_folder, registry

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, path: str):  # noqa: D107
        self.name: str = ""
        self.version: str = ""

        self.path = path
        self.load_agent_metadata()

        temp_dir = os.path.join(tempfile.gettempdir(), str(int(time.time())))

        # Copy all agent files including subfolders
        shutil.copytree(path, temp_dir, dirs_exist_ok=True)

        self.temp_dir = temp_dir

    def load_agent_metadata(self) -> None:
        """Load agent details from metadata.json."""
        metadata_path = os.path.join(self.path, "metadata.json")
        _check_metadata(Path(metadata_path))
        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

            try:
                self.name = metadata["name"]
                self.version = metadata["version"]
            except KeyError as e:
                raise ValueError(f"Missing key in metadata: {e}") from None

        if not self.version or not self.name:
            raise ValueError("Both 'version' and 'name' must be non-empty in metadata.")

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        context = {"env": env, "agent": self, "task": task}

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            sys.path.insert(0, self.temp_dir)
            runpy.run_path(AGENT_FILENAME, init_globals=context, run_name="__main__")
        finally:
            os.chdir(original_cwd)
            sys.path.pop(0)


def load_agent(name: str, local: bool = False) -> Agent:
    # TODO: Figure out how to integrate StreamerAgent as a Agent
    # if alias_or_name == "streamer":
    #     return StreamerAgent()

    if local:
        path = get_registry_folder() / name
    else:
        path = registry.download(name)

    assert path is not None, f"Agent {name} not found."
    return Agent(path.as_posix())
