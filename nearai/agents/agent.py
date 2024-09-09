# import json
# import os
# import runpy
# import shutil
# import sys
# import tempfile
# import time
# from nearai.lib import check_metadata
# from pathlib import Path
# from typing import Any, Dict, Optional, List
#
#
# from nearai.registry import get_namespace, get_registry_folder, registry
#
# AGENT_FILENAME = "agent.py"
#
#
# class Agent(object):
#     # def __init__(self, path: str):  # noqa: D107
#     def __init__(self, path: str, env_vars: Optional[Dict] = None, agent_files: Optional[List] = None, name: Optional[str] = ""):  # noqa: D107
#         self.name: str = name
#         self.path: str = path
#         self.version: str = ""
#         self.env_vars: Dict[str, Any] = env_vars if env_vars is not None else {}
#
#         self.welcome_title: Optional[str] = None
#         self.welcome_description: Optional[str] = None
#
#         self.load_agent_metadata()
#         self.namespace = get_namespace(Path(self.path))
#
#         temp_dir = os.path.join(tempfile.gettempdir(), str(int(time.time())))
#         os.makedirs(temp_dir, exist_ok=True)
#         self.temp_dir = temp_dir
#
#         for file in agent_files:
#             filename = os.path.join(temp_dir, file['filename'])
#
#             content = file['content']
#             if isinstance(content, dict):
#                 content = str(content)
#
#             with open(filename, 'w', encoding='utf-8') as f:
#                 f.write(content)
#                 print(f"Agent file {filename} created")
#
#     def load_agent_metadata(self) -> None:
#         """Load agent details from metadata.json."""
#         metadata_path = os.path.join(self.path, "metadata.json")
#         check_metadata(Path(metadata_path))
#         with open(metadata_path) as f:
#             metadata: Dict[str, Any] = json.load(f)
#             self.metadata = metadata
#
#             try:
#                 self.name = metadata["name"]
#                 self.version = metadata["version"]
#             except KeyError as e:
#                 raise ValueError(f"Missing key in metadata: {e}") from None
#
#             details = metadata.get("details", {})
#             agent = details.get("agent", {})
#             welcome = agent.get("welcome", {})
#
#             self.env_vars = details.get("env_vars", {})
#             self.welcome_title = welcome.get("title")
#             self.welcome_description = welcome.get("description")
#
#         if not self.version or not self.name:
#             raise ValueError("Both 'version' and 'name' must be non-empty in metadata.")
#
#     def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
#         if not os.path.exists(os.path.join(self.path, AGENT_FILENAME)):
#             raise ValueError("Agent run error: {AGENT_FILENAME} does not exist")
#
#         # combine agent's env_vars and user's env_vars
#         total_env_vars = {**self.env_vars, **env.env_vars}
#
#         # save os env vars
#         os.environ.update(total_env_vars)
#         # save env.env_vars
#         env.env_vars = total_env_vars
#
#         context = {"env": env, "agent": self, "task": task}
#
#         original_cwd = os.getcwd()
#         try:
#             os.chdir(self.temp_dir)
#             sys.path.insert(0, self.temp_dir)
#             runpy.run_path(AGENT_FILENAME, init_globals=context, run_name="__main__")
#         finally:
#             os.chdir(original_cwd)
#             sys.path.pop(0)
#
#
