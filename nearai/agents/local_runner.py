import json
import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, Optional

from aws_runner.service import run_with_environment
from openapi_client import EntryLocation, EntryMetadata
from shared.inference_client import InferenceClient

from nearai import CONFIG, check_metadata, plain_location
from nearai.agents.agent import Agent
from nearai.agents.environment import Environment
from nearai.config import get_hub_client
from nearai.registry import get_registry_folder, registry

DEFAULT_OUTPUT_PATH = "/tmp/nearai/conversations/"

logger = logging.getLogger(__name__)


class LocalRunner:
    def __init__(  # noqa: D107
        self,
        path,
        agents,
        thread_id,
        run_id,
        auth,
        params,
    ) -> None:
        print(
            f"Initializing LocalRunner with path: {path}, agents: {agents}, thread_id: {thread_id},"
            f"run_id: {run_id}, auth: {auth}, params: {params}"
        )

        self._agents = agents
        self._client_config = CONFIG.get_client_config()
        self._confirm_commands = True
        run_with_environment(agents, auth, thread_id, run_id, params=params)
