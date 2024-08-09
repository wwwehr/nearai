import json
import os
import re
import runpy
import sys
from dataclasses import asdict
from pathlib import Path
from subprocess import check_output, run
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
import fire
import pkg_resources
from openapi_client import EntryLocation, EntryMetadataInput
from tqdm import tqdm

import nearai
import nearai.login as nearai_login
from nearai.agent import load_agent
from nearai.benchmark import BenchmarkExecutor, DatasetInfo
from nearai.clients.lambda_client import LambdaWrapper
from nearai.config import CONFIG, DATA_FOLDER, update_config
from nearai.dataset import load_dataset
from nearai.db import db
from nearai.environment import Environment
from nearai.finetune import FinetuneCli
from nearai.hub import hub
from nearai.registry import registry
from nearai.solvers import SolverStrategy, SolverStrategyRegistry
from nearai.tensorboard_feed import TensorboardCli


class Host:
    # SSH destination
    host: str
    # URL of the supervisor API
    endpoint: str
    # Name of the cluster for this endpoint
    cluster: str

    def __init__(self, host: str, cluster: str):  # noqa: D107
        self.host = host
        url = host.split("@")[1]
        self.endpoint = f"http://{url}:8000"
        self.cluster = cluster


def parse_hosts(hosts_path: Path) -> List[Host]:
    hostnames = set()
    hosts = []
    with open(hosts_path) as f:
        for line in f:
            p = line.find("#")
            if p != -1:
                line = line[:p]
            line = line.strip(" \n")
            if not line:
                continue
            host, cluster = line.split()
            hostnames.add(host)
            hosts.append(Host(host, cluster))

    assert len(hostnames) == len(hosts), "Duplicate hosts"
    return hosts


def install(hosts_description: List[Host], skip_install: str) -> None:
    """Install supervisor on every host.

    Skip nearai installation on the dev machine (skip_install).
    """
    from fabric import ThreadingGroup as Group

    hosts_str = [h.host for h in hosts_description]
    all_hosts = Group(*hosts_str)
    install_hosts = Group(*[h.host for h in hosts_description if h.host != skip_install])

    # Check we have connection to every host
    result = all_hosts.run("hostname", hide=True, warn=False)
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, hostname: {stdout}")

    def run_bash_script(name: str) -> None:
        # Install setup_host.sh script
        script = nearai.etc(name)
        assert script.exists(), script
        install_hosts.put(script, f"/tmp/{name}")
        install_hosts.run(f"bash /tmp/{name}", warn=False)

    run_bash_script("install_cli.sh")

    nearai_path = "/home/setup/.local/bin/nearai"

    for conn in all_hosts:
        conn.run(f"{nearai_path} config set supervisor_id {conn.host}")

    all_hosts.run(f"{nearai_path} config set db_user {CONFIG.db_user}")
    all_hosts.run(f"{nearai_path} config set db_password {CONFIG.db_password}")

    result = all_hosts.run(f"{nearai_path} config get supervisor_id")
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, supervisor_id: {stdout}")

    run_bash_script("setup_supervisor.sh")


def parse_tags(tags: Union[str, Tuple[str, ...]]) -> List[str]:
    if not tags:
        return []

    elif isinstance(tags, tuple):
        return list(tags)

    elif isinstance(tags, str):
        return tags.split(",")

    else:
        raise ValueError(f"Invalid tags argument: {tags}")


entry_location_pattern = re.compile("^(?P<namespace>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)$")


def parse_location(entry_location: str) -> EntryLocation:
    """Create a EntryLocation from a string in the format namespace/name/version."""
    match = entry_location_pattern.match(entry_location)

    if match is None:
        raise ValueError(f"Invalid entry format: {entry_location}. Should have the format <namespace>/<name>/<version>")

    return EntryLocation(
        namespace=match.group("namespace"),
        name=match.group("name"),
        version=match.group("version"),
    )


class RegistryCli:
    def info(self, entry: str) -> None:
        """Show information about an item."""
        entry_location = parse_location(entry)
        metadata = registry.info(entry_location)

        if metadata is None:
            print(f"Entry {entry} not found.")
            return

        print(metadata.model_dump_json(indent=2))

    def metadata_template(self, local_path: str = "."):
        """Create a metadata template."""
        path = Path(local_path)

        metadata_path = path / "metadata.json"

        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "name": "foobar",
                    "version": "0.0.1",
                    "description": "Template metadata",
                    "category": "model",
                    "tags": ["foo", "bar"],
                    "details": {},
                    "show_entry": True,
                },
                f,
                indent=2,
            )

    def list(
        self,
        category: str = "",
        tags: str = "",
        total: int = 32,
        show_all: bool = False,
    ) -> None:
        """List available items."""
        # Make sure tags is a comma-separated list of tags
        tags_l = parse_tags(tags)
        tags = ",".join(tags_l)

        entries = registry.list(category, tags, total, show_all)

        for entry in entries:
            print(entry)

    def _check_metadata(self, path: Path):
        if not path.exists():
            print(f"Metadata file not found: {path.absolute()}")
            print("Create a metadata file with `nearai registry metadata_template`")
            exit(1)

    def update(self, local_path: str = ".") -> None:
        """Update metadata of a registry item."""
        path = Path(local_path)

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"
        self._check_metadata(metadata_path)

        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        namespace = CONFIG.auth.account_id

        entry_location = EntryLocation.model_validate(
            dict(
                namespace=namespace,
                name=metadata.pop("name"),
                version=metadata.pop("version"),
            )
        )

        entry_metadata = EntryMetadataInput.model_validate(metadata)
        result = registry.update(entry_location, entry_metadata)
        print(json.dumps(result, indent=2))

    def upload(self, local_path: str = ".") -> None:
        """Upload item to the registry."""
        path = Path(local_path).absolute()

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"
        self._check_metadata(metadata_path)

        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        namespace = CONFIG.auth.account_id

        entry_location = EntryLocation.model_validate(
            dict(
                namespace=namespace,
                name=metadata.pop("name"),
                version=metadata.pop("version"),
            )
        )

        entry_metadata = EntryMetadataInput.model_validate(metadata)
        registry.update(entry_location, entry_metadata)

        all_files = []
        total_size = 0

        # Traverse all files in the directory `path`
        for file in path.rglob("*"):
            if not file.is_file():
                continue

            relative = file.relative_to(path)

            # Don't upload metadata file.
            if file == metadata_path:
                continue

            # Don't upload backup files.
            if file.name.endswith("~"):
                continue

            # Don't upload configuration files.
            if relative.parts[0] == ".nearai":
                continue

            size = file.stat().st_size
            total_size += size

            all_files.append((file, relative, size))

        pbar = tqdm(total=total_size, unit="B", unit_scale=True)
        for file, relative, size in all_files:
            registry.upload_file(entry_location, file, relative)
            pbar.update(size)

    def download(self, entry_location_reference: str, force: bool = False) -> None:
        """Download item."""
        entry_location = parse_location(entry_location_reference)
        registry.download(entry_location, force=force, show_progress=True)


class SupervisorCli:
    def install(self) -> None:
        """Install supervisor service in current machine."""
        file = nearai.etc("supervisor.service")
        target = Path("/etc/systemd/system/nearai_supervisor.service")
        run(["sudo", "cp", str(file), str(target)])
        run(["sudo", "systemctl", "daemon-reload"])

    def start(self) -> None:
        """Start installed supervisor service in current machine."""
        run(["sudo", "systemctl", "restart", "nearai_supervisor"])

    def run(self):
        """Run supervisor app in debug mode."""
        from nearai.supervisor import run_supervisor

        run_supervisor()


class ServerCli:
    def install_supervisors(self, hosts: str, skip: str = "") -> None:
        """Install and start supervisor in every host machine."""
        hosts_l = parse_hosts(Path(hosts))
        install(hosts_l, skip)

    def start(self, hosts: str) -> None:  # noqa: D102
        from nearai.supervisor import SupervisorClient

        parsed_hosts = parse_hosts(Path(hosts))
        update_config("supervisors", [h.endpoint for h in parsed_hosts])

        db.set_all_supervisors_unavailable()

        for host in parsed_hosts:
            client = SupervisorClient(host.endpoint)
            client.init(host.cluster, host.endpoint)

        file = nearai.etc("server.service")
        target = Path("/etc/systemd/system/nearai_server.service")

        run(["sudo", "cp", str(file), str(target)])
        run(["sudo", "systemctl", "daemon-reload"])
        run(["sudo", "systemctl", "restart", "nearai_server"])

    def run(self) -> None:
        """Run server app in debug mode."""
        from nearai.server import run_server

        run_server()


class ConfigCli:
    def set(self, key: str, value: str, local: bool = False) -> None:
        """Add key-value pair to the config file."""
        update_config(key, value, local)

    def get(self, key: str) -> None:
        """Get value of a key in the config file."""
        print(CONFIG.get(key))

    def show(self) -> None:  # noqa: D102
        for key, value in asdict(CONFIG).items():
            print(f"{key}: {value}")


class BenchmarkCli:
    def run(
        self,
        dataset: str,
        solver_strategy: str,
        max_concurrent: int = -1,
        force: bool = False,
        subset: Optional[str] = None,
        **solver_kwargs: Any,
    ) -> None:
        """Run benchmark on a dataset with a solver strategy.

        It will cache the results in the database and subsequent runs will pull the results from the cache.
        If force is set to True, it will run the benchmark again and update the cache.
        """
        benchmark_id = db.get_benchmark_id(dataset, solver_strategy, force, subset=subset, **solver_kwargs)

        name, subset, dataset = dataset, subset, load_dataset(dataset)

        solver_strategy_: SolverStrategy | None = SolverStrategyRegistry.get(solver_strategy, None)
        assert (
            solver_strategy
        ), f"Solver strategy {solver_strategy} not found. Available strategies: {list(SolverStrategyRegistry.keys())}"
        solver_strategy_obj: SolverStrategy = solver_strategy_(dataset_ref=dataset, **solver_kwargs)  # type: ignore
        assert (
            name in solver_strategy_obj.compatible_datasets()
        ), f"Solver strategy {solver_strategy} is not compatible with dataset {name}"

        be = BenchmarkExecutor(DatasetInfo(name, subset, dataset), solver_strategy_obj, benchmark_id=benchmark_id)

        cpu_count = os.cpu_count()
        max_concurrent = (cpu_count if cpu_count is not None else 1) if max_concurrent < 0 else max_concurrent
        be.run(max_concurrent=max_concurrent)


class EnvironmentCli:
    def setup(self, dataset: str, task_id: int) -> None:
        """Setup environment with given task from the dataset."""
        pass

    def inspect(self, path: str) -> None:
        """Inspect environment from given path."""
        env = Environment(path, [], CONFIG, create_files=False)
        env.inspect()

    def save_folder(self, path: str, name: Optional[str] = None) -> None:
        """Saves all subfolders with agent task runs (must contain non-empty chat.txt)."""
        env = Environment(path, [], CONFIG, create_files=False)
        env.save_folder(name)

    def save_from_history(self, name: Optional[str] = None) -> None:
        """Reads piped history, finds agent task runs, writes start_command.log files, and saves to registry. For detailed usage, run: nearai environment save_from_history --help.

        This command:
        1. Finds agent task runs (must contain non-empty chat.txt)
        2. Writes start_command.log files
        3. Saves to registry

        Only 'interactive' is supported.
        Assumes format:
        ' <line_number>  <program_name> environment interactive <comma_separated_agents> <path> <other_args>'
        Run:
        $ history | grep "environment interactive" | sed "s:~:$HOME:g" | nearai environment save_from_history environment_interactive_runs_from_lambda_00
        """  # noqa: E501
        env = Environment("/", [], CONFIG, create_files=False)
        # Read from stdin (piped input)
        lines = sys.stdin.readlines()
        env.save_from_history(lines, name)

    def interactive(self, agents: str, path: str, record_run: str = "true", load_env: str = "") -> None:
        """Runs agent interactively with environment from given path."""
        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, _agents, CONFIG)
        env.run_interactive(record_run, load_env)

    def task(
        self,
        agents: str,
        task: str,
        path: str,
        max_iterations: int = 10,
        record_run: str = "true",
        load_env: str = "",
    ) -> None:
        """Runs agent non interactively with environment from given path."""
        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, _agents, CONFIG)
        env.run_task(task, record_run, load_env, max_iterations)

    def run(self, agents: str, task: str, path: str) -> None:
        """Runs agent in the current environment."""
        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, [], CONFIG)
        env.exec_command("sleep 10")
        # TODO: Setup server that will allow to interact with agents and environment

    def run_on_aws_lambda(self, agents: str, environment_id: str, auth: str, new_message: str = ""):
        """Invoke a Container based AWS lambda function to run agents on a given environment."""
        wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2"))
        wrapper.invoke_function(
            "agent-runner-docker",
            {"agents": agents, "environment_id": environment_id, "auth": json.dumps(auth), "new_message": new_message},
        )


class VllmCli:
    def run(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102
        original_argv = sys.argv.copy()
        sys.argv = [
            sys.argv[0],
        ]
        for key, value in kwargs.items():
            sys.argv.extend([f"--{key.replace('_', '-')}", str(value)])
        print(sys.argv)

        try:
            runpy.run_module("vllm.entrypoints.openai.api_server", run_name="__main__", alter_sys=True)
        finally:
            sys.argv = original_argv


class HubCLI:
    def chat(self, **kwargs):
        """Chat with model from NearAI hub.

        Args:
        ----
            query (str): User's query to model
            endpoint (str): NearAI HUB's url
            model (str): Name of a model
            provider (str): Name of a provider
            info (bool): Display system info
            kwargs (Dict[str, Any]): All cli keyword arguments

        """
        hub_query = kwargs.get("query")
        hub_endpoint = kwargs.get("endpoint", "http://127.0.0.1:8081/api/v1/chat/completions")
        hub_model = kwargs.get("model", "accounts/fireworks/models/llama-v3-70b-instruct")
        hub_provider = kwargs.get("provider", "fireworks")
        hub_info = kwargs.get("info", False)

        if not hub_query:
            return print("Error: 'query' is required for the `hub chat` command.")

        hub(hub_query, hub_endpoint, hub_model, hub_provider, hub_info)


class LoginCLI:
    def __call__(self, **kwargs):
        """Login with NEAR Mainnet account.

        Args:
        ----
            remote (bool): Remote login allows signing message with NEAR Account on a remote machine
            auth_url (str): Url to the auth portal
            accountId (str): AccountId in .near-credentials folder to signMessage
            privateKey (str): Private Key to sign a message
            kwargs (Dict[str, Any]): All cli keyword arguments

        """
        remote = kwargs.get("remote", False)
        account_id = kwargs.get("accountId", None)
        private_key = kwargs.get("privateKey", None)

        if not remote and account_id and private_key:
            nearai_login.generate_and_save_signature(account_id, private_key)
        elif not remote and account_id:
            nearai_login.login_with_file_credentials(account_id)
        else:
            auth_url = kwargs.get("auth_url", "https://auth.near.ai")
            nearai_login.login_with_near_auth(remote, auth_url)

    def status(self):
        """Load NEAR account authorization data."""
        nearai_login.print_login_status()

    def save(self, **kwargs):
        """Save NEAR account authorization data.

        Args:
        ----
            accountId (str): Near Account
            signature (str): Signature
            publicKey (str): Public Key used to sign
            callbackUrl (str): Callback Url
            nonce (str): nonce
            kwargs (Dict[str, Any]): All cli keyword arguments

        """
        account_id = kwargs.get("accountId")
        signature = kwargs.get("signature")
        public_key = kwargs.get("publicKey")
        callback_url = kwargs.get("callbackUrl")
        nonce = kwargs.get("nonce")

        if account_id and signature and public_key and callback_url and nonce:
            nearai_login.update_auth_config(account_id, signature, public_key, callback_url, nonce)
        else:
            print("Missing data")


class CLI:
    def __init__(self) -> None:  # noqa: D107
        self.registry = RegistryCli()
        self.login = LoginCLI()
        self.hub = HubCLI()

        self.supervisor = SupervisorCli()
        self.server = ServerCli()
        self.config = ConfigCli()
        self.benchmark = BenchmarkCli()
        self.environment = EnvironmentCli()
        self.finetune = FinetuneCli()
        self.tensorboard = TensorboardCli()
        self.vllm = VllmCli()

    def submit(self, command: str, name: str, nodes: int = 1, cluster: str = "truthwatcher") -> None:
        """Submit task."""
        from nearai.server import ServerClient

        author = CONFIG.get_user_name()

        client = ServerClient(CONFIG.server_url)

        # Check we can connect to the server
        client.status()

        # Detect in-progress git action
        # https://adamj.eu/tech/2023/05/29/git-detect-in-progress-operation/
        operation = ["CHERRY_PICK_HEAD", "MERGE_HEAD", "REBASE_HEAD", "REVERT_HEAD"]
        for op in operation:
            result = run(["git", "rev-parse", "--verify", op], capture_output=True)
            if result.returncode == 0:
                print(f"Detected in-progress git operation: {op}")
                return

        repository_url = check_output(["git", "remote", "-v"]).decode().split("\n")[0].split("\t")[1].split()[0]
        commit = check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        diff = check_output(["git", "diff", "HEAD"]).decode()

        submission_result = client.submit(name, repository_url, commit, command, author, diff, nodes, cluster)

        print("experiment id:", submission_result["experiment"]["id"])

    def inference(self) -> None:
        """Submit inference task."""
        raise NotImplementedError()

    def location(self) -> None:  # noqa: D102
        print(nearai.cli_path())

    def version(self) -> None:  # noqa: D102
        # TODO: Show current commit or tag
        print(pkg_resources.get_distribution("nearai").version)

    def update(self) -> None:
        """Update nearai version."""
        path = DATA_FOLDER / "nearai"

        if path.absolute() != nearai.cli_path().absolute():
            print()
            print(f"Updating nearai version installed in {path}")
            print(f"The invoked nearai is in {nearai.cli_path()}")
            print()

        if path.exists():
            run(["git", "pull"], cwd=path)

    def status(self) -> None:
        """Show status of the cluster."""
        from nearai.server import ServerClient

        client = ServerClient(CONFIG.server_url)
        status = client.status()

        for experiment in status.get("last_experiments", []):
            experiment["diff_len"] = len(experiment.pop("diff", ""))

        print(json.dumps(status))


def main() -> None:
    # TODO: Check for latest version and prompt to update.
    fire.Fire(CLI)
