import hashlib
import json
import logging
import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union, cast

import psutil

from runner.agent import Agent
from runner.tool_registry import ToolRegistry

DELIMITER = "\n"
CHAT_FILENAME = "chat.txt"
SYSTEM_LOG_FILENAME = "system_log.txt"
AGENT_LOG_FILENAME = "agent_log.txt"
TERMINAL_FILENAME = "terminal.txt"
ENVIRONMENT_FILENAME = "environment.tar.gz"

# TODO(#290): Add API endpoints for nearai/config defaults
DEFAULT_PROVIDER = "fireworks"
DEFAULT_MODEL = "llama-v3p1-405b-instruct-long"
DEFAULT_PROVIDER_MODEL = f"fireworks::accounts/fireworks/models/{DEFAULT_MODEL}"
PROVIDER_MODEL_SEP = "::"


class Environment(object):
    def __init__(  # noqa: D107
        self,
        path: str,
        agents: List["Agent"],
        client,
        server_url: str = "https://api.near.ai",
        create_files: bool = True,
        metric_function=None,
        env_vars: Optional[Dict[str, Any]] = None,
        print_system_log: bool = False,
    ):
        self._path = path
        self._agents = agents
        self._done = False
        self._server_url = server_url
        self._client = client
        self._metric_function = metric_function
        self._tools = ToolRegistry()
        self.register_standard_tools()
        self.env_vars: Dict[str, Any] = env_vars if env_vars else {}
        self._last_used_model = ""
        self.print_system_log = print_system_log

        if create_files:
            os.makedirs(self._path, exist_ok=True)
            open(os.path.join(self._path, CHAT_FILENAME), "a").close()
        os.chdir(self._path)

    @staticmethod
    def _generate_run_id() -> str:
        return uuid.uuid4().hex

    def get_tool_registry(self) -> ToolRegistry:  # noqa: D102
        return self._tools

    def register_standard_tools(self) -> None:  # noqa: D102
        reg = self.get_tool_registry()
        reg.register_tool(self.exec_command)
        reg.register_tool(self.read_file)
        reg.register_tool(self.write_file)
        reg.register_tool(self.request_user_input)
        reg.register_tool(self.list_files)

    def add_message(self, role: str, message: str, filename: str = CHAT_FILENAME, **kwargs: Any) -> None:  # noqa: D102
        with open(os.path.join(self._path, filename), "a") as f:
            f.write(json.dumps({"role": role, "content": message, **kwargs}) + DELIMITER)

    def add_system_log(self, log: str, level: int = logging.INFO) -> None:
        """Add system log with timestamp and log level."""
        logger = logging.getLogger("system_logger")
        if not logger.handlers:
            # Configure the logger if it hasn't been set up yet
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(os.path.join(self._path, SYSTEM_LOG_FILENAME))
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            if self.print_system_log:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

        # Log the message
        logger.log(level, log)

    def add_agent_log(self, log: str, level: int = logging.INFO) -> None:
        """Add agent log with timestamp and log level."""
        logger = logging.getLogger("agent_logger")
        if not logger.handlers:
            # Configure the logger if it hasn't been set up yet
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(os.path.join(self._path, AGENT_LOG_FILENAME))
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Log the message
        logger.log(level, log)

    def _add_agent_start_system_log(self, agent_idx: int) -> None:
        """Add agent start system log."""
        agent = self._agents[agent_idx]
        message = f"Starting an agent {agent.name}"
        if agent.model != "":
            model = self.get_model_for_inference(agent.model)
            self._last_used_model = model
            message += f" that will connect to {model}"
            if agent.model_temperature:
                message += f", temperature={agent.model_temperature}"
            if agent.model_max_tokens:
                message += f", max_tokens={agent.model_max_tokens}"
        self.add_system_log(message)

    def list_terminal_commands(self, filename: str = TERMINAL_FILENAME) -> List[Any]:  # noqa: D102
        return self.list_messages(filename)

    def list_messages(self, filename: str = CHAT_FILENAME) -> List[Any]:  # noqa: D102
        path = os.path.join(self._path, filename)

        if not os.path.exists(path):
            return []

        with open(path, "r") as f:
            return [json.loads(message) for message in f.read().split(DELIMITER) if message]

    def list_files(self, path: str) -> List[str]:
        """Lists files in the environment.

        path: The path to list files from.
        """
        return os.listdir(os.path.join(self._path, path))

    def get_path(self) -> str:  # noqa: D102
        return self._path

    def read_file(self, filename: str) -> str:
        """Read a file from the environment.

        filename: The name of the file to read.
        """
        if not os.path.exists(os.path.join(self._path, filename)):
            return ""
        try:
            with open(os.path.join(self._path, filename), "r") as f:
                return f.read()
        except Exception as e:
            return f"failed to read file: {e}"

    def write_file(self, filename: str, content: str) -> str:
        """Writes a file to the environment.

        filename: The name of the file to write to
        content: The content to write to the file.
        """
        path = Path(self._path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Successfully wrote {len(content) if content else 0} characters to {filename}"

    def exec_command(self, command: str) -> Dict[str, str]:
        """Executes a command in the environment and logs the output.

        command: The command to execute.
        """
        try:
            process = subprocess.Popen(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                universal_newlines=True,
                cwd=self._path,
            )
        except Exception as e:
            return {
                "command": command,
                "returncode": 999,
                "stdout": "",
                "stderr": "Failed to execute: " + str(e),
            }

        msg = ""

        def kill_process_tree(p: Any) -> None:
            nonlocal msg
            msg = "Killing process due to timeout"

            process = psutil.Process(p.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()

        timer = threading.Timer(2, kill_process_tree, (process,))
        timer.start()
        process.wait()
        timer.cancel()

        result = {
            "command": command,
            "stdout": process.stdout.read() if process.stdout and hasattr(process.stdout, "read") else "",
            "stderr": process.stderr.read() if process.stderr and hasattr(process.stderr, "read") else "",
            "returncode": process.returncode,
            "msg": msg,
        }
        with open(os.path.join(self._path, TERMINAL_FILENAME), "a") as f:
            f.write(json.dumps(result) + DELIMITER)
        return result

    def get_model_for_inference(self, model: str = "") -> str:
        """Returns 'provider::model_full_path' or 'model_short_name' if provider is default or not given."""
        provider = self._agents[0].model_provider if self._agents else ""
        if model == "":
            model = self._agents[0].model if self._agents else ""
        if model == "":
            return DEFAULT_PROVIDER_MODEL

        # TODO(#312): On CLI we do 'model_short_name' -> 'provider::model_full_path' here.
        if provider == "" or provider == DEFAULT_PROVIDER:
            return model
        return provider + PROVIDER_MODEL_SEP + model

    def _run_inference_completions(
        self,
        messages: Iterable[Any] | str,
        model: Iterable[Any] | str,
        stream: bool,
        **kwargs: Any,
    ) -> Any:
        """Run inference completions for given parameters."""
        if isinstance(messages, str):
            self.add_system_log("Deprecated completions call. Pass `messages` as a first parameter.", logging.WARNING)
            messages_or_model = messages
            model_or_messages = model
            model = cast(str, messages_or_model)
            messages = cast(Iterable[Any], model_or_messages)
        else:
            model = cast(str, model)
            messages = cast(Iterable[Any], messages)
        model = self.get_model_for_inference(model)
        if model != self._last_used_model:
            self._last_used_model = model
            self.add_system_log(f"Connecting to {model}")
        return self._client.completions(
            model,
            messages,
            stream=stream,
            temperature=self._agents[0].model_temperature if self._agents else None,
            max_tokens=self._agents[0].model_max_tokens if self._agents else None,
            **kwargs,
        )

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completions(
        self, messages: Iterable[Any] | str, model: Iterable[Any] | str = "", stream: bool = False, **kwargs: Any
    ) -> Any:
        """Returns all completions for given messages using the given model."""
        return self._run_inference_completions(messages, model, stream, **kwargs)

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completions_and_run_tools(
        self,
        messages: Iterable[Any] | str,
        model: Iterable[Any] | str,
        tools: Optional[List] = None,
        **kwargs: Any,
    ) -> Any:
        """Returns all completions for given messages using the given model and runs tools."""
        stream = kwargs.get("stream", False)
        response = self._run_inference_completions(messages, model, stream=stream, tools=tools, **kwargs)
        response_message = response["choices"][0]["message"]

        if hasattr(response_message, "tool_calls") and response_message["tool_calls"]:
            for tool_call in response_message["tool_calls"]:
                function_name = tool_call["function.name"]
                assert function_name, "Tool call must have a function name"
                function_args = json.loads(tool_call.function.arguments)
                function_response = self._tools.call_tool(function_name, **function_args)

                if function_response:
                    function_response_json = json.dumps(function_response) if function_response else ""
                    self.add_message("tool", function_response_json, tool_call_id=tool_call.id, name=function_name)
        return response

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completion(self, messages: Iterable[Any] | str, model: Iterable[Any] | str = "") -> str:
        """Returns a completion for the given messages using the given model."""
        result = self.completions(model, messages)
        response_message = result["choices"][0]["message"]["content"]
        assert response_message, "No completions returned"
        return response_message

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completion_and_run_tools(
        self,
        messages: Iterable[Any] | str,
        model: Iterable[Any] | str,
        tools: Optional[List] = None,
        **kwargs: Any,
    ) -> str:
        """Returns a completion for the given messages using the given model and runs tools."""
        completion_tools_response = self.completions_and_run_tools(model, messages, tools, **kwargs)
        response_message = completion_tools_response["choices"][0]["message"]["content"]
        assert response_message, "No completions returned"
        return response_message

    def call_agent(self, agent_path: int, task: str) -> None:
        """Calls agent with given task."""
        self._agents[agent_path].run(self, task=task)

    def get_agents(self) -> List["Agent"]:
        """Returns list of agents available in environment."""
        return self._agents

    def is_done(self) -> bool:  # noqa: D102
        return self._done

    def mark_done(self) -> None:  # noqa: D102
        self._done = True

    def create_snapshot(self) -> bytes:
        """Create an in memory snapshot."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            with tarfile.open(fileobj=f, mode="w:gz") as tar:
                tar.add(self._path, arcname=".")
            f.flush()
            f.seek(0)
            snapshot = f.read()
        return snapshot

    def save_to_registry(
        self,
        path: str,
        run_type: str,
        run_id: str,
        base_id: Optional[Union[str, int]] = None,
    ) -> str:
        """Save Environment to Registry.

        :return: The name of the saved environment.
        """
        save_start_time = time.perf_counter()
        full_agent_name = self._agents[0].name if self._agents else "unknown"
        safe_agent_name = full_agent_name.replace("/", "_")
        generated_name = f"environment_run_{safe_agent_name}_{run_id}"
        name = generated_name

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            with tarfile.open(fileobj=f, mode="w:gz") as tar:
                tar.add(path, arcname=".")
            f.flush()
            f.seek(0)
            snapshot = f.read()
            tar_filename = f.name

            timestamp = datetime.now(timezone.utc).isoformat()
            description = f"Agent {run_type} {safe_agent_name} {run_id} {timestamp}"
            details = {
                "base_id": base_id,
                "timestamp": timestamp,
                "agents": [agent.name for agent in self._agents],
                "run_id": run_id,
                "run_type": run_type,
                "filename": tar_filename,
            }
            tags_l = ["environment"]
            request_start_time = time.perf_counter()
            registry_id = self._client.save_environment(
                file=snapshot,
                name=name,
                description=description,
                details=details,
                tags=tags_l,
            )
            request_stop_time = time.perf_counter()
            if self._metric_function:
                self._metric_function("SaveEnvironmentToRegistry_Duration", request_stop_time - request_start_time)
            print(
                f"Saved environment {registry_id} to registry. To load use flag `--load-env={registry_id}`. "
                f"or `--load-env={name}`"
            )
            save_stop_time = time.perf_counter()
            if self._metric_function:
                self._metric_function("SaveEnvironment_Duration", save_stop_time - save_start_time)
            return registry_id

    def load_snapshot(self, snapshot: bytes) -> None:
        """Load Environment from Snapshot."""
        shutil.rmtree(self._path, ignore_errors=True)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            f.write(snapshot)
            f.flush()
            f.seek(0)

            with tarfile.open(fileobj=f, mode="r:gz") as tar:
                tar.extractall(self._path)

    def __str__(self) -> str:  # noqa: D105
        return f"Environment({self._path})"

    def run_agent(self, task: Optional[str]) -> None:  # noqa: D102
        self._agents[0].run(self, task=task)

    def request_user_input(self) -> None:
        """Must be called to request input from the user."""
        self.set_next_actor("user")

    def set_next_actor(self, who: str) -> None:  # noqa: D102
        next_action_fn = os.path.join(self._path, ".next_action")

        with open(next_action_fn, "w") as f:
            f.write(who)

    def get_next_actor(self) -> str:  # noqa: D102
        next_action_fn = os.path.join(self._path, ".next_action")

        if os.path.exists(next_action_fn):
            with open(next_action_fn) as f:
                return f.read().strip(" \n")
        else:
            # By default the user starts the conversation.
            return "user"

    def run(
        self,
        new_message: str,
        record_run: bool = True,
        load_env: str = "",
        max_iterations: int = 10,
    ) -> Optional[str]:
        """Runs agent(s) against a new or previously created environment."""
        run_id = self._generate_run_id()
        base_id = load_env
        iteration = 0

        self._add_agent_start_system_log(agent_idx=0)

        self.set_next_actor("agent")

        if new_message:
            self.add_message("user", new_message)

        while iteration < max_iterations and not self.is_done() and self.get_next_actor() != "user":
            iteration += 1
            self._agents[0].run(self, task=new_message)

        if record_run:
            return self.save_to_registry(self._path, "remote run", run_id, base_id)
        return None

    def contains_non_empty_chat_txt(self, directory: str) -> bool:  # noqa: D102
        chat_txt_path = os.path.join(directory, "chat.txt")
        return os.path.isfile(chat_txt_path) and os.path.getsize(chat_txt_path) > 0

    def generate_folder_hash_id(self, path: str) -> str:
        """Returns id similar to _generate_run_id(), but based on files and their contents in path, including subfolders."""  # noqa: E501
        hash_obj = hashlib.md5()

        for root, _dirs, files in os.walk(path):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        hash_obj.update(chunk)

        return hash_obj.hexdigest()
