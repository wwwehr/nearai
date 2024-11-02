import io
import json
import os
import runpy
import shutil
import socket
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from shared.client_config import ClientConfig

AGENT_FILENAME = "agent.py"


class _UniqueDirectoryGenerator:
    """Thread-safe unique temporary directory path generator."""

    _lock = threading.Lock()
    _counter = 0

    @classmethod
    def generate_unique_path(cls, prefix="agent"):
        """Generates a guaranteed unique temporary directory path.

        Args:
        ----
            prefix (str): Prefix for the directory name

        Returns:
        -------
            str: Unique temporary directory path

        """
        with cls._lock:
            # Increment counter atomically
            cls._counter += 1
            counter = cls._counter

        components = [
            prefix,
            uuid.uuid4().hex,  # Random UUID
            str(int(time.time() * 1000000)),  # High-resolution timestamp (microseconds)
            str(os.getpid()),  # Process ID
            socket.gethostname(),  # Hostname
            str(threading.get_ident()),  # Thread ID
            str(counter),  # Atomic counter
        ]

        # Create a hash of all components to keep the path length reasonable
        unique_hash = uuid.uuid5(uuid.NAMESPACE_DNS, "_".join(components)).hex

        return os.path.join(tempfile.gettempdir(), f"{prefix}_{unique_hash}")

    @staticmethod
    def create_unique_dir(prefix="agent"):
        """Generates a unique path and creates the directory.

        Args:
        ----
            prefix (str): Prefix for the directory name

        Returns:
        -------
            str: Path to the created directory

        Raises:
        ------
            OSError: If directory creation fails

        """
        path = _UniqueDirectoryGenerator.generate_unique_path(prefix)
        os.makedirs(path, exist_ok=False)  # Raises OSError if directory exists
        return path


class Agent(object):
    def __init__(self, identifier: str, agent_files: Union[List, Path], metadata: Dict):  # noqa: D107
        self.identifier = identifier
        name_parts = identifier.split("/")
        self.namespace = name_parts[0]
        self.name = name_parts[1]
        self.version = name_parts[2]

        self.metadata = metadata
        self.env_vars: Dict[str, Any] = {}

        self.model = ""
        self.model_provider = ""
        self.model_temperature: Optional[float] = None
        self.model_max_tokens: Optional[int] = None
        self.max_iterations = 1
        self.welcome_title: Optional[str] = None
        self.welcome_description: Optional[str] = None

        self.set_agent_metadata(metadata)
        self.agent_files = agent_files
        self.original_cwd = os.getcwd()

        self.temp_dir = self.write_agent_files_to_temp(agent_files)

    @staticmethod
    def write_agent_files_to_temp(agent_files):
        """Write agent files to a temporary directory."""
        temp_dir = _UniqueDirectoryGenerator.create_unique_dir()

        if isinstance(agent_files, List):
            os.makedirs(temp_dir, exist_ok=True)

            for file_obj in agent_files:
                file_path = os.path.join(temp_dir, file_obj["filename"])

                try:
                    if not os.path.exists(os.path.dirname(file_path)):
                        os.makedirs(os.path.dirname(file_path))

                    content = file_obj["content"]

                    if isinstance(content, dict) or isinstance(content, list):
                        try:
                            content = json.dumps(content)
                        except Exception as e:
                            print(f"Error converting content to json: {e}")
                        content = str(content)

                    if isinstance(content, str):
                        content = content.encode("utf-8")

                    with open(file_path, "wb") as f:
                        with io.BytesIO(content) as byte_stream:
                            shutil.copyfileobj(byte_stream, f)
                except Exception as e:
                    print(f"Error writing file {file_path}: {e}")
                    raise e

        else:
            # if agent files is a PosixPath, it is a path to the agent directory
            # Copy all agent files including subfolders
            shutil.copytree(agent_files, temp_dir, dirs_exist_ok=True)

        return temp_dir

    def set_agent_metadata(self, metadata) -> None:
        """Set agent details from metadata."""
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

        if agent_metadata := details.get("agent", None):
            if defaults := agent_metadata.get("defaults", None):
                self.model = defaults.get("model", self.model)
                self.model_provider = defaults.get("model_provider", self.model_provider)
                self.model_temperature = defaults.get("model_temperature", self.model_temperature)
                self.model_max_tokens = defaults.get("model_max_tokens", self.model_max_tokens)
                self.max_iterations = defaults.get("max_iterations", self.max_iterations)

        if not self.version or not self.name:
            raise ValueError("Both 'version' and 'name' must be non-empty in metadata.")

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        if not os.path.exists(os.path.join(self.temp_dir, AGENT_FILENAME)):
            raise ValueError(f"Agent run error: {AGENT_FILENAME} does not exist")

        # combine agent.env_vars and env.env_vars
        total_env_vars = {**self.env_vars, **env.env_vars}

        # save os env vars
        os.environ.update(total_env_vars)
        # save env.env_vars
        env.env_vars = total_env_vars

        context = {"env": env, "agent": self, "task": task}

        try:
            os.chdir(self.temp_dir)
            sys.path.insert(0, self.temp_dir)
            runpy.run_path(AGENT_FILENAME, init_globals=context, run_name="__main__")
        finally:
            os.chdir(self.original_cwd)
            sys.path.pop(0)

    @staticmethod
    def load_agents(agents: str, config: ClientConfig, local: bool = False):
        """Loads agents from the registry."""
        return [Agent.load_agent(agent, config, local) for agent in agents.split(",")]

    @staticmethod
    def load_agent(
        name: str,
        config: ClientConfig,
        local: bool = False,
    ):
        """Loads a single agent from the registry."""
        from nearai.registry import get_registry_folder, registry

        identifier = None
        if local:
            agent_files_path = get_registry_folder() / name
            if config.auth is None:
                namespace = "not-logged-in"
            else:
                namespace = config.auth.account_id
        else:
            agent_files_path = registry.download(name)
            identifier = name
        assert agent_files_path is not None, f"Agent {name} not found."

        metadata_path = os.path.join(agent_files_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        if not identifier:
            identifier = "/".join([namespace, metadata["name"], metadata["version"]])

        return Agent(identifier, agent_files_path, metadata)
