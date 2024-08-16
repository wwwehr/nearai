import os
import runpy
import shutil
import sys
import tempfile
import time
from typing import Any, Optional

from nearai.registry import get_registry_folder, registry

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, name: str, version: str, path: str, code: str, temp_dir: str):  # noqa: D107
        self.name = name
        self.version = version
        self.path = path
        self.code = code
        self.temp_dir = temp_dir

    @staticmethod
    def from_disk(path: str) -> "Agent":
        """Path must contain alias and version.

        .../agents/<alias>/<version>/agent.py
        """
        parts = path.split("/")

        agent_temp_dir = os.path.join(tempfile.gettempdir(), str(int(time.time())))

        # Copy all agent files including subfolders
        shutil.copytree(path, agent_temp_dir, dirs_exist_ok=True)

        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], path, f.read(), agent_temp_dir)

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
        if not path.exists():
            raise ValueError(f"Local agent {path} not found.")
    else:
        path = registry.download(name)

    assert path is not None, f"Agent {name} not found."
    return Agent.from_disk(path.as_posix())
