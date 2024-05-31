import json
from dataclasses import asdict
from pathlib import Path
from subprocess import check_output, run
from typing import List, Optional

import fire
import pkg_resources
from fabric import ThreadingGroup as Group
from tabulate import tabulate

import jasnah
from jasnah.benchmark import BenchmarkExecutor
from jasnah.completion import create_completion_fn
from jasnah.config import CONFIG, DATA_FOLDER, update_config
from jasnah.dataset import load_dataset
from jasnah.db import db
from jasnah.registry import Registry, dataset, model, registry
from jasnah.server import ServerClient, run_server
from jasnah.solvers import SolverStrategy, SolverStrategyRegistry
from jasnah.supervisor import SupervisorClient, run_supervisor


class Host:
    # SSH destination
    host: str
    # URL of the supervisor API
    endpoint: str
    # Name of the cluster for this endpoint
    cluster: str

    def __init__(self, host: str, cluster: str):
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


def install(hosts_description: List[Host], skip_install: str):
    """
    Install supervisor on every host.
    Skip jasnah-cli installation on the dev machine (skip_install)
    """
    hosts_str = [h.host for h in hosts_description]
    all_hosts = Group(*hosts_str)
    install_hosts = Group(*[h.host for h in hosts_description if h.host != skip_install])

    # Check we have connection to every host
    result = all_hosts.run("hostname", hide=True, warn=False)
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, hostname: {stdout}")

    def run_bash_script(name):
        # Install setup_host.sh script
        script = jasnah.etc(name)
        assert script.exists(), script
        install_hosts.put(script, f"/tmp/{name}")
        install_hosts.run(f"bash /tmp/{name}", warn=False)

    run_bash_script("install_cli.sh")

    jasnah_cli_path = "/home/setup/.local/bin/jasnah-cli"

    for conn in all_hosts:
        conn.run(f"{jasnah_cli_path} config set supervisor_id {conn.host}")

    all_hosts.run(f"{jasnah_cli_path} config set db_user {CONFIG.db_user}")
    all_hosts.run(f"{jasnah_cli_path} config set db_password {CONFIG.db_password}")

    result = all_hosts.run(f"{jasnah_cli_path} config get supervisor_id")
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, supervisor_id: {stdout}")

    run_bash_script("setup_supervisor.sh")


def parse_tags(tags) -> List[str]:
    if not tags:
        return []

    elif isinstance(tags, tuple):
        return list(tags)

    elif isinstance(tags, str):
        assert "," not in tags
        return [tags]

    else:
        raise ValueError(f"Invalid tags argument: {tags}")


class RegistryCli:
    def __init__(self, registry: Registry):
        self._registry = registry

    def add(self, s3_path: str, description: str, name: Optional[str] = None, tags: str = "", **details):
        """Add an item to the registry that was previously uploaded to S3"""
        tags = parse_tags(tags)
        assert self._registry.exists_in_s3(s3_path), f"Item {s3_path} does not exist in S3"
        self._registry.add(
            s3_path=s3_path,
            author=CONFIG.get_user_name(),
            description=description,
            name=name,
            show_entry=True,
            tags=tags,
            details=details,
        )

    def add_tags(self, identifier: int, tags: str):
        """Add tags to an item in the registry"""
        tags = parse_tags(tags)
        self._registry.add_tags(identifier, tags)

    def remove_tag(self, identifier: int, tag: str):
        self._registry.remove_tag(identifier, tag)

    def list(self, total: int = 16, show_all: bool = False, verbose: bool = False, tags: str = ""):
        """List available items"""
        tags = parse_tags(tags)

        header = ["id", "path", "name", "description", "tags"]

        if verbose:
            header += ["author", "show_entry", "time"]

        table = [header]

        for entry_with_tags in self._registry.list(tags=tags, total=total, show_all=show_all):
            entry = entry_with_tags.entry
            tags = ", ".join(entry_with_tags.tags)

            row = [
                entry.id,
                entry.path,
                entry.name,
                entry.description,
                tags,
            ]

            if verbose:
                row += [entry.author, entry.show_entry, entry.time]

            table.append(row)

        print(tabulate(table, headers="firstrow"))

    def update(
        self,
        identifier: int,
        *,
        author: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: Optional[bool] = None,
    ):
        """Update item in the registry"""
        self._registry.update(
            identifier=identifier,
            author=author,
            description=description,
            name=name,
            details=details,
            show_entry=show_entry,
        )

    def info(self):
        """Show information about an item"""
        raise NotImplementedError()

    def upload(
        self,
        path: str,
        s3_path: str,
        description: str,
        name: Optional[str] = None,
        show_entry: bool = True,
        tags: str = "",
        **details,
    ):
        """Upload item to the registry"""
        tags = parse_tags(tags)

        author = CONFIG.get_user_name()
        self._registry.upload(
            path=Path(path),
            s3_path=s3_path,
            author=author,
            description=description,
            name=name,
            details=details,
            show_entry=show_entry,
            tags=tags,
        )

    def download(self, name: str):
        """Download item"""
        self._registry.download(name)


class SupervisorCli:
    def install(self):
        """Install supervisor service in current machine"""
        file = jasnah.etc("supervisor.service")
        target = Path("/etc/systemd/system/jasnah_supervisor.service")
        run(["sudo", "cp", str(file), str(target)])
        run(["sudo", "systemctl", "daemon-reload"])

    def start(self):
        """Start installed supervisor service in current machine"""
        run(["sudo", "systemctl", "restart", "jasnah_supervisor"])

    def run(self):
        """Run supervisor app in debug mode"""
        run_supervisor()


class ServerCli:
    def install_supervisors(self, hosts: str, skip: str = ""):
        """Install and start supervisor in every host machine"""
        hosts = parse_hosts(hosts)
        install(hosts, skip)

    def start(self, hosts: str):
        parsed_hosts = parse_hosts(hosts)
        update_config("supervisors", [h.endpoint for h in parsed_hosts])

        db.set_all_supervisors_unavailable()

        for host in parsed_hosts:
            client = SupervisorClient(host.endpoint)
            client.init(host.cluster, host.endpoint)

        file = jasnah.etc("server.service")
        target = Path("/etc/systemd/system/jasnah_server.service")

        run(["sudo", "cp", str(file), str(target)])
        run(["sudo", "systemctl", "daemon-reload"])
        run(["sudo", "systemctl", "restart", "jasnah_server"])

    def run(self):
        """Run server app in debug mode"""
        run_server()


class ConfigCli:
    def set(self, key: str, value: str, local: bool = False):
        """Add key-value pair to the config file"""
        update_config(key, value, local)

    def get(self, key: str):
        """Get value of a key in the config file"""
        print(CONFIG.get(key))

    def show(self):
        for key, value in asdict(CONFIG).items():
            print(f"{key}: {value}")


class BenchmarkCli:
    def __init__(self, datasets: RegistryCli, models: RegistryCli):
        self.datasets = datasets
        self.models = models

    def run(self, dataset: str, model: str, solver_strategy: str, subset: str = None):
        name, subset, dataset = dataset, subset, load_dataset(dataset)
        model_completion_fn = create_completion_fn(model)

        solver_strategy: SolverStrategy | None = SolverStrategyRegistry.get(solver_strategy, None)
        assert (
            solver_strategy
        ), f"Solver strategy {solver_strategy} not found. Available strategies: {list(SolverStrategyRegistry.keys())}"
        solver_strategy = solver_strategy(model_completion_fn, dataset_ref=dataset)
        assert (
            name in solver_strategy.compadible_datasets()
        ), f"Solver strategy {solver_strategy} is not compatible with dataset {name}"

        be = BenchmarkExecutor((name, subset, dataset), solver_strategy)
        be.run()


class CLI:
    def __init__(self):
        self.registry = RegistryCli(registry)
        self.datasets = RegistryCli(dataset)
        self.models = RegistryCli(model)

        self.supervisor = SupervisorCli()
        self.server = ServerCli()
        self.config = ConfigCli()
        self.benchmark = BenchmarkCli(self.datasets, self.models)

    def submit(self, command: str, name: str, nodes: int = 1, cluster: str = "truthwatcher"):
        """Submit task"""
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

        result = client.submit(name, repository_url, commit, command, author, diff, nodes, cluster)

        print("experiment id:", result["experiment"]["id"])

    def inference(self):
        """Submit inference task"""
        raise NotImplementedError()

    def location(self):
        print(jasnah.cli_path())

    def version(self):
        # TODO: Show current commit or tag
        print(pkg_resources.get_distribution("jasnah").version)

    def update(self):
        """Update jasnah-cli version"""
        path = DATA_FOLDER / "jasnah-cli"

        if path.absolute() != jasnah.cli_path().absolute():
            print()
            print(f"Updating jasnah-cli version installed in {path}")
            print(f"The invoked jasnah-cli is in {jasnah.cli_path()}")
            print()

        if path.exists():
            run(["git", "pull"], cwd=path)

    def status(self):
        """Show status of the cluster"""
        client = ServerClient(CONFIG.server_url)
        status = client.status()

        for experiment in status.get("last_experiments", []):
            experiment["diff_len"] = len(experiment.pop("diff", ""))

        print(json.dumps(status))


def main():
    fire.Fire(CLI)
