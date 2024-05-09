import shutil
from pathlib import Path
from subprocess import run

import fire
import pkg_resources

import jasnah
from jasnah import registry
from jasnah.server import install, parse_hosts
from jasnah.supervisor import run_supervisor


class RegistryCli:
    def __init__(self, registry: registry.Registry):
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
        run(["sudo", "systemctl", "start", "jasnah_supervisor"])

    def run(self):
        """Run supervisor app in debug mode"""
        run_supervisor()


class ServerCli:
    def install(self, hosts: str):
        hosts = parse_hosts(hosts)
        install(hosts)

    def start(self):
        raise NotImplementedError()


class CLI:
    def __init__(self):
        self.dataset = RegistryCli(registry.dataset)
        self.model = RegistryCli(registry.model)
        self.supervisor = SupervisorCli()
        self.server = ServerCli()

    def submit(self):
        """Submit task"""
        raise NotImplementedError()

    def inference(self):
        """Submit inference task"""
        raise NotImplementedError()

    def config(self):
        """Configure jasnah-cli settings"""
        # TODO: Host, database url, author
        raise NotImplementedError()

    def location(self):
        print(jasnah.cli_path())

    def version(self):
        print(pkg_resources.get_distribution("jasnah").version)


def main():
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
