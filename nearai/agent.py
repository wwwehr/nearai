import sys
import os
import runpy
import tempfile
from typing import Any, Dict, List, Optional

from nearai.registry import get_registry_folder, registry

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, name: str, version: str, path: str, code: str, imports: List[Dict[str, str]]):  # noqa: D107
        self.name = name
        self.version = version
        self.path = path
        self.code = code
        # python files in the agent folder
        self.imports = imports

    @staticmethod
    def from_disk(path: str) -> "Agent":
        """Path must contain alias and version.

        .../agents/<alias>/<version>/agent.py
        """
        parts = path.split("/")

        # collect agent python files
        agent_imports = []
        for filename in os.listdir(path):
            if filename != AGENT_FILENAME and filename.endswith('.py'):
                file_path = os.path.join(path, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    code = file.read()
                    agent_imports.append({
                        'file_name': filename,
                        'code': code
                    })

        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], path, f.read(), agent_imports)

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        context = {"env": env, "agent": self, "task": task}

        import_files = []
        agent_temp_dir = tempfile.gettempdir()

        def run_script(script_name):
            original_cwd = os.getcwd()
            try:
                os.chdir(agent_temp_dir)
                sys.path.insert(0, agent_temp_dir)
                runpy.run_path(script_name, init_globals=context, run_name="__main__")
            finally:
                os.chdir(original_cwd)
                sys.path.pop(0)

        # save all python code from agent folder in `agent_temp_dir`
        for object_to_import in self.imports:
            import_file_path = os.path.join(agent_temp_dir, object_to_import['file_name'])
            with open(import_file_path, 'w+', encoding='utf-8') as import_file:
                import_file.write(object_to_import['code'])
                import_file.flush()  # Ensure content is written to disk
                import_files.append(import_file_path)

        # save agent code in `agent_temp_dir`
        agent_file_path = os.path.join(agent_temp_dir, AGENT_FILENAME)
        with open(agent_file_path, 'w+', encoding='utf-8') as code_file:
            code_file.write(self.code)
            code_file.flush()  # Ensure content is written to disk

        # run all python files from agent folder
        for import_file_path in import_files:
            run_script(import_file_path)

        # run agent
        if agent_file_path:
            run_script(agent_file_path)

        # remove temp files
        for import_file_path in import_files:
            os.remove(import_file_path)
        if agent_file_path:
            os.remove(agent_file_path)


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
