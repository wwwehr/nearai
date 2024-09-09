import json
import os
import shutil
from typing import Dict, Any, Optional, List

# from nearai.agents.agent import Agent
from aws_runner.agents.agent import Agent
from nearai.lib import check_metadata

from nearai.registry import get_registry_folder, registry
from pathlib import Path


class LocalAgent(Agent):
    def __init__(self, path: str, env_vars: Optional[Dict] = None, agent_files: Optional[List] = None,
                 name: Optional[str] = ""):
        super().__init__(path, env_vars, agent_files, name)
        self.metadata = None

    def load_agent_metadata(self) -> None:
        """Load agent details from metadata.json."""
        metadata_path = os.path.join(self.path, "metadata.json")

        check_metadata(Path(metadata_path))

        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)
            self.metadata = metadata

            try:
                self.name = metadata["name"]
                self.version = metadata["version"]
            except KeyError as e:
                raise ValueError(f"Missing key in metadata: {e}") from None

            details = metadata.get("details", {})
            agent = details.get("agent", {})
            welcome = agent.get("welcome", {})

            self.env_vars = details.get("env_vars", {})
            self.welcome_title = welcome.get("title")
            self.welcome_description = welcome.get("description")

        if not self.version or not self.name:
            raise ValueError("Both 'version' and 'name' must be non-empty in metadata.")


def load_agent(name: str, local: bool = False) -> Agent:
    # TODO: Figure out how to integrate StreamerAgent as a Agent
    # if alias_or_name == "streamer":
    #     return StreamerAgent()

    if local:
        path = get_registry_folder() / name
    else:
        path = registry.download(name)

    assert path is not None, f"Agent {name} not found."

    agent = LocalAgent(path.as_posix())
    agent.load_agent_metadata()

    # Copy all agent files including subfolders
    shutil.copytree(path, agent.temp_dir, dirs_exist_ok=True)

    return agent
