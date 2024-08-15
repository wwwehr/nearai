import json
import os
from typing import Any, Dict, List, Optional

from nearai.registry import get_registry_folder, registry

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, name: str, version: str, path: str, code: str, imports: List[str]):  # noqa: D107
        self.name = name
        self.version = version
        self.path = path
        self.code = code
        self.imports = imports

    @staticmethod
    def from_disk(path: str) -> "Agent":
        """Path must contain alias and version.

        .../agents/<alias>/<version>/agent.py
        """
        parts = path.split("/")

        agent_imports = []
        metadata_path = os.path.join(path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                metadata: Dict[str, Any] = json.load(f)

            imports = metadata.get("imports", [])
            if isinstance(imports, list):
                for import_file in imports:
                    import_file_path = os.path.join(path, import_file)
                    if not os.path.exists(import_file_path):
                        raise ValueError(f"Agent import file {import_file_path} not found.")
                    with open(import_file_path) as i:
                        agent_imports.append(i.read())
        else:
            raise ValueError("Agent metadata not found.")

        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], path, f.read(), agent_imports)

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        d = {"env": env, "agent": self, "task": task}

        for import_code in self.imports:
            exec(import_code, d, d)

        exec(self.code, d, d)


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
