from pathlib import Path
from subprocess import check_output, run

import fire
import pkg_resources

import jasnah
from jasnah.config import CONFIG, DATA_FOLDER, update_config
from jasnah.registry import Registry, dataset, model
from jasnah.server import install, parse_hosts
from jasnah.server_app import ServerClient, run_server
from jasnah.supervisor import run_supervisor


class RegistryCli:
    def __init__(self, registry: Registry):
        self._registry = registry

    def list(self) -> None:
        """List available items"""
        self._registry.list()

    def upload(self, path: str, name: str) -> None:
        """Upload item"""
        self._registry.upload(Path(path), name)

    def get(self, name: str) -> None:
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
        hosts = parse_hosts(hosts)
        endpoints = [f"http://{x.split('@')[1]}:8000" for x in hosts]
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
        print(CONFIG)


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
            check_output(["git", "remote", "-v"]).decode().split("\n")[0].split("\t")[1].split()[0]
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
