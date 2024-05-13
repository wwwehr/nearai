from dataclasses import asdict
from pathlib import Path
from subprocess import check_output, run
from typing import List

import fire
import pkg_resources
from fabric import Connection
from fabric import ThreadingGroup as Group

import jasnah
from jasnah.config import CONFIG, DATA_FOLDER, update_config
from jasnah.registry import Registry, dataset, model
from jasnah.server import ServerClient, run_server
from jasnah.supervisor import run_supervisor


class Host:
    # SSH destination
    host: str
    # URL of the supervisor API
    api_endpoint: str

    def __init__(self, host: str):
        self.host = host
        url = host.split("@")[1]
        self.api_endpoint = f"http://{url}:8000"


def parse_hosts(hosts_path: Path) -> List[Host]:
    hosts = []
    with open(hosts_path) as f:
        for line in f:
            p = line.find("#")
            if p != -1:
                line = line[:p]
            line = line.strip(" \n")
            if not line:
                continue
            hosts.append(line)

    assert len(set(hosts)) == len(hosts), ("Duplicate hosts", hosts)
    return [Host(x) for x in hosts]


def install(hosts_description: List[Host]):
    """Install supervisor on every host."""
    hosts = Group(*hosts_description)

    # Check we have connection to every host
    result = hosts.run("hostname", hide=True, warn=False)
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, hostname: {stdout}")

    # Install setup_host.sh script
    setup_script = jasnah.etc("setup_host.sh")
    assert setup_script.exists(), setup_script
    hosts.put(setup_script, "/tmp/setup_host.sh")

    # Install supervisor
    hosts.run("bash /tmp/setup_host.sh", warn=False)

    def set_supervisor_id(conn: Connection):
        conn.run(["jasnah-cli", "config", "set", "supervisor_id", conn.host])

    hosts.run(set_supervisor_id, warn=False)


class RegistryCli:
    def __init__(self, registry: Registry):
        self._registry = registry

    def list(self):
        """List available items"""
        self._registry.list()

    def upload(self, path: str, name: str):
        """Upload item"""
        self._registry.upload(Path(path), name)

    def get(self, name: str):
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
    def install_supervisors(self, hosts: str):
        """Install and start supervisor in every host machine"""
        hosts = parse_hosts(hosts)
        install(hosts)

    def start(self, hosts: str):
        parsed_hosts = parse_hosts(hosts)
        endpoints = [h.api_endpoint for h in parsed_hosts]
        update_config("supervisors", endpoints)

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

    def show(self):
        for key, value in asdict(CONFIG).items():
            print(f"{key}: {value}")


class CLI:
    def __init__(self):
        self.dataset = RegistryCli(dataset)
        self.model = RegistryCli(model)
        self.supervisor = SupervisorCli()
        self.server = ServerCli()
        self.config = ConfigCli()

    def submit(self, command: str):
        """Submit task"""
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

        repository_url = (
            check_output(["git", "remote", "-v"])
            .decode()
            .split("\n")[0]
            .split("\t")[1]
            .split()[0]
        )
        commit = check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        diff = check_output(["git", "diff", "HEAD"]).decode()

        client.submit(repository_url, commit, diff, command)

    def inference(self):
        """Submit inference task"""
        raise NotImplementedError()

    def location(self):
        print(jasnah.cli_path())

    def version(self):
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


def main():
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
